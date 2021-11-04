# Introduction

This repo holds scripts used for making a dataset of domain names that is extracted from the external links on pages from all the language-specific Wikipedia sites.

Published as OCTO-023: https://www.icann.org/octo-023-en.pdf

# Software

Both of the programs below store logs and output files in `~/wikipedia-dataset`, which they create if it is not already there.

## `wiki_get_domains_from_databases.py`

This program collects the relevant databases from Wikipedia, processes each file.

The command line options are:

- `--replace` is only needed if you already have created the database and have not deleted it before the next run.
- `--date` sets the date to be used as the source date. If not specified, it defaults to the first day of the current month. Informal observations show that it takes at least a few days for the database backup to complete.
- `--sources` is the domain name from which to get the Wikipedia data. It defaults to a server in the US. Note that some mirrors rate limit downloads after a set limit, so downloading might take a while.
- `--subset_size` is the number of domain namnes to store in the sample file. It defaults to 150,000, which should be sufficient to make a real subset of 100,000 names with IPv4 addresses.

The program puts out a file called `all-domains.txt`.
It also creates a file called `sample-of-NNNN.txt`, where `NNNN` is the sample size chosen.

The program requires the `curl` and `gunzip` programs to run.

##`wiki_results.py`

This program takes the file of sample domain names as input, and analyzes the domain names in that file.
It then puts out a smaller sample file where all the names have at least one IPv4 address.

The command line options are:

- `--input_file` is the name of the input file; it defaults to "sample-of-150000.txt".
- `--subset_size` is the number of names to take from the input file. The default is 100,000.
- `--limit_input` is used for testing, Set the value to the number of names you want to test; 0 (the default) means all names.

The results shown are the percentage of names that have IPv6 addresses, and the percentage of names that are DNSSEC-signed. More results are likely to be added later.

The program requires the `getdns_query` program to run. This is available in most package managers in "getdns-utils".

## Logs

An example of the log output from the two programs is:

	2021-02-08 21:07:03,159 Started wiki_get_domains_from_databases run
	2021-02-08 21:07:03,159 Using dumps.wikimedia.your.org for sources
	2021-02-08 21:07:03,159 Using 20210201 for source date
	2021-02-08 21:07:03,694 Found 747 wiki names in https://dumps.wikimedia.your.org/backup-index.html
	2021-02-08 21:07:03,695 Started getting the files
	2021-02-08 22:39:57,849 Done getting files
	2021-02-08 22:39:57,851 Starting processing database files for domain names
	2021-02-08 23:50:57,101 Starting collecting domains from processed databases
	2021-02-08 23:51:08,571 Saving all_domains.txt with 7438701 names
	2021-02-08 23:51:13,232 Making a sample of 150000 names
	2021-02-08 23:51:14,004 Saved /home/researcher/wikipedia-dataset/sample-of-150000.txt
	2021-02-08 23:51:14,004 Finished wiki_get_domains_from_databases run
	2021-02-09 00:15:27,326 Starting extract_addresses on 150000 records in /home/researcher/wikipedia-dataset/sample-of-150000.txt
	2021-02-09 13:03:09,121 42584 names did not have an IPv4 address
	2021-02-09 13:03:09,182 Processing 107416 domains took 46061 seconds
	2021-02-09 13:03:09,183 Of 150000 names in, 107416 (72%) had IPv4 addresses
	2021-02-09 13:03:09,183 Of those domains, 4% had DNSSEC and 18% had IPv6 addresses
	2021-02-09 13:03:09,183 Culling results to 100000 values
	2021-02-09 13:03:09,391 Finished extract_addresses run

# License

Note that the dataset that is derived here is derived from Wikipedia data, it is in no way associated with Wikipedia itself.
See the [Wikimedia license](https://en.wikipedia.org/wiki/Wikipedia:Text_of_Creative_Commons_Attribution-ShareAlike_3.0_Unported_License) and [general information](https://en.wikipedia.org/wiki/Wikipedia:Copyrights) for more detail on the license associated with Wikipedia’s data.
