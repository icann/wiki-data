#!/usr/bin/env python3
import argparse, concurrent.futures, logging, json, os, pickle, random, subprocess, tempfile, time

# Check if getdns_request is installed
try:
	r = subprocess.run("getdns_query -h", shell=True, capture_output=True, check=True)
except:
	exit("Could not run 'getdns_query -h'. Exiting.") 

def get_dns_for_one_name(this_name):
	# Takes a domain name, does a query using getdns_query, and returns a dict of information about it
	dict_to_return = {"4": [], "6": [], "D": 0}
	# Using a temp file to hold two commands lets getdns_query run the two queries in parallel
	with tempfile.NamedTemporaryFile(mode="w+t") as temp_f:
		temp_file_name = temp_f.name
		temp_f.write(f"-j -t 4000 +dnssec {this_name} a\n-j -t 4000 {this_name} aaaa\n")
		temp_f.flush()
		try:
			r = subprocess.run(f"getdns_query -a -B -F {temp_file_name}", shell=True, capture_output=True, encoding="latin-1", check=True)
		except Exception as e:
			log(f"During lookup on {this_name}: {e}")
			return dict_to_return
		this_stdout = r.stdout
	# Get the two replies
	try:
		(a_dnssec_reply, aaaa_reply) = this_stdout.splitlines()
	except Exception as e:
		debug(f"Got {e} when splitting reply for {this_name}: {this_stdout}")
		return dict_to_return
	try:
		a_dnssec_dict = json.loads(a_dnssec_reply)
	except Exception as e:
		debug(f"Bad JSON for a_dnssec_dict '{e}' for {this_name}: {a_dnssec_reply}")
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
		log(f"For v4 address extraction for {this_name}, got {e} for {a_addr_list}")
		return dict_to_return
	# Parse for AAAA addresses
	try:
		aaaa_dict = json.loads(aaaa_reply)
	except Exception as e:
		debug(f"Bad JSON for aaaa_reply {e} for {this_name}: {a_dnssec_reply}")
		return dict_to_return
	aaaa_addr_list = aaaa_dict.get("just_address_answers")
	try:
		for this_rec in aaaa_addr_list:
			if this_rec["address_type"] == "IPv6":
				dict_to_return["6"].append(this_rec["address_data"])
	except Exception as e:
		log(f"For v6 address extraction for {this_name}, got {e} for {aaaa_addr_list}")
		return dict_to_return
	# Get DNSSEC info
	try:
		dict_to_return["D"] = a_dnssec_dict["replies_tree"][0]["dnssec_status"]
	except Exception as e:
		log(f"For DNSSEC checking on {this_name}, got {e}:\n{a_dnssec_dict['replies_tree']}")
		return dict_to_return
	return dict_to_return

if __name__ == "__main__":
	# Directory locations
	main_dir = os.path.expanduser("~/wikipedia-dataset")
	
	# Set up the logging and alert mechanisms
	log_file_name = f"{main_dir}/log.txt"
	debug_file_name = f"{main_dir}/debug.txt"
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
		log(f"{error_message}. Exiting.")
		exit()
	
	this_parser = argparse.ArgumentParser()
	this_parser.add_argument("--subset_size", action="store", dest="subset_size", type=int, default=100000,
		help="Size of subset file to keep")
	this_parser.add_argument("--limit_input", action="store", dest="limit_input", type=int, default=0,
		help="Number of domains to test; 0 means all")
	this_parser.add_argument("--input_file", action="store", dest="input_file", default=f"{main_dir}/sample-of-150000.txt",
		help="Size of subset file to keep")
	opts = this_parser.parse_args()

	# Get the initial set of names
	if not os.path.exists(opts.input_file):
		die(f"Could not find {opts.input_file}")
	all_names = open(opts.input_file, "rt").read().splitlines()
	
	# If opts.limit_input is >0, limit the number of names to what is given 
	if opts.limit_input > 0:
		all_names = random.sample(all_names, opts.limit_input)
	
	log(f"Starting extract_addresses on {len(all_names)} records in {opts.input_file}")

	dns_results = {}
	dns_failed = []
	dns_time_start = time.time()
	with concurrent.futures.ProcessPoolExecutor() as executor:
		for (this_name, returned_dict) in zip(all_names, executor.map(get_dns_for_one_name, all_names, chunksize=10000)):
			if len(returned_dict["4"]) == 0:
				dns_failed.append(this_name)
			else:
				dns_results[this_name] = returned_dict
	
	log(f"{len(dns_failed)} names did not have an IPv4 address")

	dnssec_total = 0
	ipv6_total = 0
	for this_name in dns_results:
		if dns_results[this_name]["D"] == 400:
			dnssec_total += 1
		if len(dns_results[this_name]["6"]) > 0:
			ipv6_total += 1
	log(f"Processing {len(dns_results)} domains took {int(time.time()-dns_time_start)} seconds")
	log(f"Of {len(all_names)} names in, {len(all_names) - len(dns_failed)} ({100 - len(dns_failed)/len(all_names):.1f}%) had IPv4 addresses")
	log(f"Of those domains, {100*(dnssec_total/len(dns_results)):.1f}% had DNSSEC response of 400 and {100*(ipv6_total/len(dns_results)):.1f}% had IPv6 addresses")
	
	# Keep the list of just the samples
	dns_samples = {}

	log(f"Culling results to {opts.subset_size} values")
	sample_names = list(dns_results.keys())
	sample_names = sample_names[:opts.subset_size]
	for this_name in sample_names:
		dns_samples[this_name] = dns_results[this_name]
	
	# Save the files
	out_f = open(f"{main_dir}/dns_samples.pickle", "wb")
	pickle.dump(dns_samples, out_f)
	out_f.close()
	out_f = open(f"{main_dir}/dns_failed.txt", "wt")
	for this_name in dns_failed:
		out_f.write(f"{this_name}\n")
	out_f.close()
		
	log("Finished extract_addresses run")
