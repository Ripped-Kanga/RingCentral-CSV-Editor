#!/usr/bin/python

__author__ = "Alan Saunders"
__purpose__ = ""
__version__ = "0.1"
__github__ = "https://github.com/Ripped-Kanga/RingCentral-CSV-Editor\n"
__disclaimer__ = ""


# Import Libraries
import sys
import os
from helper.csv_helper import RingCentralCSV

def main():
	rc_csv = RingCentralCSV()

	csv_in_name = input("Specify the csv file name: ")
	print ("Printing CSV File:\n")

	rc_csv.checker(csv_in_name)

	print (f"The data of {csv_in_name} is displayed above, review before continuing...")
	csv_changes = []
	first_name = input("What is the new contact first name? ")
	last_name = input("What is the new contact last name? ")
	mobile = input("What is the new contact mobile number? ")
	csv_changes.extend([first_name,last_name,mobile])
	print (csv_changes)


# Start Execution
if __name__ == "__main__":
	# Start main() and listen for keyboard interrupts
	try:
		main()
	except KeyboardInterrupt:
		print('\nInterrupted by keyboard CTRL + C, exiting...\n')
		try:
			sys.exit(130)
		except SystemExit:
			os._exit(130)