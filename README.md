# Introduction

This repo holds scripts used for making a dataset of domain names that is extracted from the external links on pages from all the language-specific Wikipedia sites.

(When the new OCTO document is published, put a link here)

# Software

Both of the programs below store logs and output files in `~/wikipedia-dataset`, which they create if it is not already there.

## `wiki_get_domains_from_databases.py`

This program collects the relevant databases from Wikipedia, processes each file.

The command line options are:

- `--replace` is only needed if you already have created the database and have not deleted it befor the next run.
- `--date` sets the date to be used as the source date. If not specified, it defaults to the first day of the current month. Informal observations show that it takes at least a few days for the database backup to complete.
- `--sources` is the domain name from which to get the Wikipedia data. It defaults to a server in the US.
- `--subset_size` is the number of domain namnes to store in the sample file. It defaults to 150,000, which should be sufficient to make a real subset of 100,000 names with IPv4 addresses.

The program puts out a file called `all_domains.txt`.
It also creates a file called `sample-of-NNNN.txt`, where `NNNN` is the sample size chosen.

The program requires the `curl` and `gunzip` programs to run.

##`wiki_results.py`

This program takes the file of sample names as input, and analyzes the domain names in that file.

The command line options are:

- `--input_file` is the name of the input file; it defaults to "sample-of-150000.txt".
- `--subset_size` is the number of names to take from the sample file. The default is 100,000.
- `--limit_input` is used for testing, Set the value to the number of names you want to test; 0 (the default) means all names.

The results shown are the percentage of names that have IPv6 addresses, and the percentage of names that are DNSSEC-signed. More results are likely to be added later.

The program requires the `getdns_query` program to run. This is available in most package managers in "getdns-utils".

# License

Note that the dataset that is derived here is derived from Wikipedia data, it is in no way associated with Wikipedia itself.
See the [Wikimedia license](https://en.wikipedia.org/wiki/Wikipedia:Text_of_Creative_Commons_Attribution-ShareAlike_3.0_Unported_License) and [general information](https://en.wikipedia.org/wiki/Wikipedia:Copyrights) for more detail on the license associated with Wikipedia’s data.
