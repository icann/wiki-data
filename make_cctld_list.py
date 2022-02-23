#!/usr/bin/env python3
import logging, os

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

	# This file needs to be defined before options are parsed
	all_domains_filename = f"{main_dir}/all-domains.txt"
	if not os.path.exists(all_domains_filename):
		die(f"Could not find {all_domains_filename}")
	cctld_domains_filename = f"{main_dir}/just-cctld-domains.txt"	

	log("Started make_cctld_list run")
	
	just_cctlds = set()	
	for this_line in open(all_domains_filename, mode="rt").read().splitlines():
		parts = this_line.split(".")
		if len(parts[-1]) == 2:
			just_cctlds.add(this_line)
	
	# Save the file
	log(f"Saving just_cctlds.txt with {len(just_cctlds)} names")
	with open(cctld_domains_filename, mode="wt") as out_f:
		for this_domain in just_cctlds:
			out_f.write(f"{this_domain}\n")
	log(f"Saved {cctld_domains_filename}")
	
