#!/usr/bin/python

__author__ = "Alan Saunders"
__purpose__ = ""
__version__ = "0.1"
__github__ = "https://github.com/Ripped-Kanga/RingCentral-CSV-Editor\n"
__disclaimer__ = ""


# Import Libraries
from helper.csv_helper import RingCentralCSV

def main():
	rc_csv = RingCentralCSV()
	process_name = rc_csv._test("alan")
	print (process_name)

	print ("Printing CSV File:\n")

	rc_csv.csv_reader(input("Specify the csv file name: "))


if __name__ == "__main__":
	main()