#!/usr/bin/env python3
import argparse, datetime, glob, logging, os, random, re, subprocess, tempfile

# Check if curl and gunzip are installed
try:
	r = subprocess.run("curl --help", shell=True, capture_output=True, check=True)
except:
	exit("Could not run 'curl --help'. Exiting.")
try:
	r = subprocess.run("gunzip --help", shell=True, capture_output=True, check=True)
except:
	exit("Could not run 'gunzip --help'. Exiting.")

# Processes an external links file for one Wikipedia site
#   Takes a file name, returns nothing, writes out a text file with a similar name
def process_one_file(this_file):
	this_short_name = (os.path.basename(this_file).split("-", maxsplit=1))[0]
	# Save all input for later use
	just_names_unique = set()
	# Unzip the input file
	with tempfile.NamedTemporaryFile() as temp_f:
		temp_file_name = temp_f.name
		# Some files are listed as .gz but are short text files that are error text; ignore them
		if os.path.getsize(this_file) < 500:
			return
		# Use external gzip instead of Python's library because Python's library fails for odd reasons when gunzip does not
		try:
			subprocess.run(f"gunzip -c {this_file} >{temp_file_name}", shell=True, capture_output=False, check=True)
		except Exception as e:
			log(f"Could not unzip {this_file}: {e}")
			return
		in_f = open(temp_file_name, mode="rt", encoding="latin-1")
		# Here is where a system on a computer that was running MySQL would just load the files using MySQL commands.
		#   However, setting up MySQL for something as trivial as this job is tedious.
		#   Also, each file creates a table of the same table name, so if this is to be done, some processing on the incoming file needs to be done anyway.
		#   Having said that, if somone wants to write some code that first checks for the presence of MySQL, then adds all the names to just_names_unique,
		#      that would be just dandy.
		# Instead, go through the files using heuristics about MySQL dumps
		for this_line in in_f:
			# Short lines do not have INSERT commands
			if len(this_line) < 1000:
				continue
			if not this_line[0:35] == "INSERT INTO `externallinks` VALUES ":
				debug(f"Found a long line with bad beginning '{this_line[0:35]}' in {this_file}.")
				return
			if not this_line.endswith(";\n"):
				debug(f"Found a long line that didn't end with semicolon: '{this_line[-25:]}' in {this_file}. ")
				return
			real_line = this_line[36:-2]  # Strip off "INSERT INTO..." and ";\n"
			# Each INSERT INTO has multiple tuples for insertion
			these_tuples = real_line.split("),(")
			for this_tuple in these_tuples:
				# Each tuple has three parts, and we only care about the last part
				try:
					(_, _, rest_of_tuple) = this_tuple.split(",", maxsplit=2)
					(saved_url, _) = rest_of_tuple[1:].split("','", maxsplit=1)
				except:
					# Ignore tuples and URLs that have errors. This means we are probably losing some possibly-interestind data.
					#   A possible to-do is to save these to a debug log and see if we could handle them more creatively than just ignoring them.
					continue
				# Break the URL into scheme and rest; skip the URL if the scheme doesn't have a colon
				try:
					(scheme, rest) = saved_url.split(":", maxsplit=1)
				except:
					continue
				# Lots of bad URLs seem to be schemes that start with "//" or have URL remnants, so ignore all these
				if scheme.startswith("//") or "&" in scheme or "%" in scheme or "?" in scheme or "," in scheme:
					continue
				# Only save domain names from http: and https:
				if not scheme.lower() in ("http", "https"):
					continue
				# From here on out, we forget the scheme. If it later becomes important, it needs to be saved (probalby in its .lowercase() form)
				# Get the rest, which should start with "//" but doesn't always
				if rest.startswith("//"):
					rest = rest[2:]
				# Split off everything past the domain name
				if "/" in rest:
					(domain_name, _) = rest.split("/", maxsplit=1)
				else:
					domain_name = rest
				# Name without a . are mistakes; that is, no URLs should lead to just a TLD
				if not "." in domain_name:
					continue
				# Make the domain name lowercase
				domain_name = domain_name.lower()
				# Remove port numbers if they are there
				if ":" in domain_name:
					domain_name = domain_name[:domain_name.index(":")]
				# Lots of cruft slips in the domain names
				if re.search("[^\.a-z0-9]", domain_name):
					continue
				# Remove the IPv4 addresses by seeing if the last label is a decimal number (which would not be a TLD)
				if (domain_name.split(".")[-1]).isdigit():
					continue
				# Look for beginning dots
				if domain_name.startswith("."):
					continue
				# Look for ".."
				if ".." in domain_name:
					continue
				# Eliminate domain names that have become empty with the processing above
				if domain_name == "":
					continue
				# Finally, put it in the set
				just_names_unique.add(domain_name)
		# Write out file in domains_dir
		f_out = open(f"{domains_dir}/{this_short_name}.txt", "wt")
		for this_domain in just_names_unique:
			f_out.write(f"{this_domain}\n")
		f_out.close()
		return

if __name__ == "__main__":
	# Directory locations
	main_dir = os.path.expanduser("~/wikipedia-dataset")
	originals_dir = f"main_dir{}/Originals"
	domains_dir = f"{main_dir}/Domains"
	# Make sure each directory exists
	for this_dir in [main_dir, originals_dir, domains_dir]:
		try:
			os.mkdir(this_dir)
		except:
			pass
	
	all_domains_filename = f"{main_dir}/all_domains.txt"
	
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
	this_parser.add_argument("--replace", action="store_true", dest="replace",
		help="fReplace the {all_domains_filename} file if it already exists")
	this_parser.add_argument("--date", action="store", dest="date", default="",
		help="Date to use for pulling sources")
	this_parser.add_argument("--sources", action="store", dest="sources", default="dumps.wikimedia.your.org",
		help="Domain name to get sources from")
	this_parser.add_argument("--subset_size", action="store", dest="subset_size", type=int, default=150000,
		help="Size of subset file to keep")
	opts = this_parser.parse_args()

	if (not opts.replace) and os.path.exists(all_domains_filename):
		die(f"Didn't start because {all_domains_filename} exists and --replace was not specified")

	log("Started wiki_get_domains_from_databases run")

	# Where to find the sources for the domain names
	log(f"Using {opts.sources} for sources")
	source_doc = f"https://{opts.sources}/backup-index.html"
	
	# The the date specified, or default to the first day of the current month
	if opts.date:
		source_date = opts.date
	else:
		today_date = datetime.date.today()
		source_date = f"{today_date.year}{today_date.month:02}01"
	log(f"Using {source_date} for source date")

	names_of_wikipedias = set()
	# Get the main file that lists all the types of wikis
	try:
		r = subprocess.run(f"curl --silent {source_doc}", shell=True, capture_output=True, check=True)
	except Exception as e:
		die(f"Getting {source_doc} failed with '{e}'.")
	in_all = r.stdout.decode("utf-8")
	for this_string in  re.finditer("\".*?wiki.*?/20", in_all):
		names_of_wikipedias.add(this_string.group()[1:-3])
	log(f"Found {len(names_of_wikipedias)} wiki names in {source_doc}")

	# Get each file
	#   This is done without mulitprocessing in order to not overload the mirror server.
	#   This uses curl because some of the files are very large and can mess work badly in small VMs.
	log("Started getting the files")
	names_without_content = []
	do_not_get = ("commonswiki")  # This one is huge, and doesn't contain any domain names not in the others
	for this_name in sorted(names_of_wikipedias):
		if this_name in do_not_get:
			continue
		file_name = f"{this_name}-{source_date}-externallinks.sql.gz"
		full_out_file_name = f"{originals_dir}/{file_name}"
		# Don't get files that are already there
		if os.path.exists(full_out_file_name):
			continue
		this_url = f"https://{opts.sources}/{this_name}/{source_date}/{file_name}"
		try:
			r = subprocess.run(f"curl {this_url} --silent -o {full_out_file_name}", shell=True, capture_output=False, check=True)
		except Exception:
			names_without_content.append(this_name)
			continue
	if len(names_without_content) > 0:
		log(f"{len(names_without_content)} names without content: {" ".join(names_without_content)}")
	log("Done getting files")

	log("Starting processing database files for domain names")
	# There is no strong need to run this under concurrent.futures because it takes around an hour even single-threaded
	all_database_files = sorted(glob.glob(f"{originals_dir}/*"))
	for this_file in all_database_files:
		process_one_file(this_file)
	# Note that the result of this is a set of files, each of which has the unique domain names for that language
	#   Another method would be to have process_one_file update a single set. This was not chosen in case it was useful to look at the intermediate output.
	
	# Colllect all the domain files, make a master set of domians
	log("Starting collecting domains from processed databases")
	all_domain_files = sorted(glob.glob(f"{domains_dir}/*"))
	full_domain_set = set()
	for this_file in all_domain_files:
		for this_domain in open(this_file, "rt").read().splitlines():
			full_domain_set.add(this_domain)

	# Save the file
	log(f"Saving all_domains.txt with {len(full_domain_set)} names")
	for this_domain in full_domain_set:
		out_f.write(f"{this_domain}\n")
	out_f.close()
	
	# Pick a random sample and save it
	log("Making a sample of {opts.subset_size} names")
	rand_domains = random.sample(list(full_domain_set), opts.subset_size)
	sample_file_name = f"{main_dir}/sample-of-{opts.subset_size}.txt"
	out_f = open(sample_file_name, "wt")
	for this_domain in rand_domains:
		out_f.write(f"{this_domain}\n")
	out_f.close()
	log(f"Saved {sample_file_name}")
		
	log("Finished wiki_get_domains_from_databases run")
