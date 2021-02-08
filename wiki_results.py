#!/usr/bin/env python3
import argparse, concurrent.futures, logging, json, os, pickle, random, subprocess, tempfile, time

# Check if getdns_request is installed
try:
	r = subprocess.run("getdns_query -h", shell=True, capture_output=True, check=True)
except:
	exit("Could not run 'getdns_query -h'. Exiting.")

def get_dns_for_one_name(this_name):
	# Takes a domain name, does a query using getdns_query, and returns a dict of information about it
	dict_to_return = {"4": [], "6": [], "D": False}
	# Using a temp file to hold two commands lets getdns_query run the two queries in parallel
	with tempfile.NamedTemporaryFile(mode="w+t") as temp_f:
		temp_file_name = temp_f.name
		temp_f.write("-j -t 4000 +dnssec {0} a\n-j -t 4000 {0} aaaa\n".format(this_name))
		temp_f.flush()
		try:
			r = subprocess.run("getdns_query -a -B -F {}".format(temp_file_name), shell=True, capture_output=True, encoding="utf-8", check=True)
		except Exception as e:
			log("During lookup on {}, got '{}'".format(this_name, e))
			return dict_to_return
	this_stdout = r.stdout
	# Get the two replies
	try:
		(a_dnssec_reply, aaaa_reply) = this_stdout.splitlines()
	except Exception as e:
		debug("Got {} when splitting reply for {}: {}".format(e, this_name, this_stdout))
		return dict_to_return
	try:
		a_dnssec_dict = json.loads(a_dnssec_reply)
	except Exception as e:
		debug("Bad JSON for a_dnssec_dict'{}' for {}: {}".format(e, this_name, a_dnssec_reply))
		return dict_to_return
	# Parse for A addresses; if there are no A addresses, return {}
	a_addr_list = a_dnssec_dict.get("just_address_answers")
	# Stop if there are no A records
	if not a_addr_list:
		return dict_to_return
	try:
		for this_rec in a_addr_list:
			if this_rec["address_type"] == "IPv4":
				dict_to_return["4"].append(this_rec["address_data"])
	except Exception as e:
		log("For v4 address extraction for {}, got {} for {}".format(this_name, e, a_addr_list))
		return dict_to_return
	# Parse for AAAA addresses
	try:
		aaaa_dict = json.loads(aaaa_reply)
	except Exception as e:
		debug("Bad JSON for aaaa_reply'{}' for {}: {}".format(e, this_name, a_dnssec_reply))
		return dict_to_return
	aaaa_addr_list = aaaa_dict.get("just_address_answers")
	try:
		for this_rec in aaaa_addr_list:
			if this_rec["address_type"] == "IPv6":
				dict_to_return["6"].append(this_rec["address_data"])
	except Exception as e:
		log("For v6 address extraction for {}, got {} for {}".format(this_name, e, aaaa_addr_list))
		return dict_to_return
	# Get DNSSEC info
	try:
		if (a_dnssec_dict["replies_tree"])[0]["dnssec_status"] == 400:
			dict_to_return["D"] = True
	except Exception as e:
		log("For DNSSEC checking on {}, got {}:\n{}".format(this_name, e, a_dnssec_dict["replies_tree"]))
		return dict_to_return
	return dict_to_return

if __name__ == "__main__":
	# Directory locations
	main_dir = os.path.expanduser("~/wikipedia-dataset")
	
	# Set up the logging and alert mechanisms
	log_file_name = "{}/log.txt".format(main_dir)
	debug_file_name = "{}/debug.txt".format(main_dir)
	this_log = logging.getLogger("logging")
	this_log.setLevel(logging.INFO)
	this_debug = logging.getLogger("alerts")
	this_debug.setLevel(logging.DEBUG)
	log_handler = logging.FileHandler(log_file_name)
	log_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
	this_log.addHandler(log_handler)
	debug_handler = logging.FileHandler(debug_file_name)
	debug_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
	this_debug.addHandler(debug_handler)
	def log(log_message):
		this_log.info(log_message)
	def debug(log_message):
		this_debug.info(log_message)
	def die(error_message):
		log("{}. Exiting.".format(error_message))
		exit()
	
	this_parser = argparse.ArgumentParser()
	this_parser.add_argument("--subset_size", action="store", dest="subset_size", type=int, default=100000,
		help="Size of subset file to keep")
	this_parser.add_argument("--limit_input", action="store", dest="limit_input", type=int, default=0,
		help="Number of domains to test; 0 means all")
	this_parser.add_argument("--input_file", action="store", dest="input_file", default="{}/sample-of-150000.txt".format(main_dir),
		help="Size of subset file to keep")
	opts = this_parser.parse_args()

	# Get the initial set of names
	if not os.path.exists(opts.input_file):
		die("Could not find {}".format(opts.input_file))
	all_names = open(opts.input_file, "rt").read().splitlines()
	
	# If opts.limit_input is >0, limit the number of names to what is given 
	if opts.limit_input > 0:
		all_names = random.sample(all_names, opts.limit_input)
	
	log("Starting extract_addresses on {} records in {}".format(len(all_names), opts.input_file))

	dns_results = {}
	dns_failed = []
	dns_time_start = time.time()
	with concurrent.futures.ProcessPoolExecutor() as executor:
		for (this_name, returned_dict) in zip(all_names, executor.map(get_dns_for_one_name, all_names, chunksize=10000)):
			if len(returned_dict["4"]) == 0:
				dns_failed.append(this_name)
			else:
				dns_results[this_name] = returned_dict
	
	log("{} names did not have an IPv4 address".format(len(dns_failed)))

	dnssec_total = 0
	ipv6_total = 0
	for this_name in dns_results:
		if dns_results[this_name]["D"]:
			dnssec_total += 1
		if len(dns_results[this_name]["6"]) > 0:
			ipv6_total += 1
	log("Processing {} domains took {} seconds".format(len(dns_results), int(time.time()-dns_time_start)))
	log("Of {} names in, {} ({}%) had IPv4 addresses".format(len(all_names), len(all_names) - len(dns_failed), 100 - int(100*(len(dns_failed)/len(all_names)))))
	log("Of those domains, {}% had DNSSEC and {}% had IPv6 addresses".format(int(100*(dnssec_total/len(dns_results))), int(100*(ipv6_total/len(dns_results)))))
	
	# Keep the list of just the samples
	dns_samples = {}

	log("Culling results to {} values".format(opts.subset_size))
	sample_names = list(dns_results.keys())
	sample_names = sample_names[:opts.subset_size]
	for this_name in sample_names:
		dns_samples[this_name] = dns_results[this_name]
	
	# Save the files
	out_f = open("{}/dns_samples.pickle".format(main_dir), "wb")
	pickle.dump(dns_samples, out_f)
	out_f.close()
	out_f = open("{}/dns_failed.txt".format(main_dir), "wt")
	for this_name in dns_failed:
		out_f.write("{}\n".format(this_name))
	out_f.close()
		
	log("Finished extract_addresses run")
