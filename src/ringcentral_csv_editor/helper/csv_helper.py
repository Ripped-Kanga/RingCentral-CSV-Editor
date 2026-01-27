#!/usr/bin/python

# Import Libraries
import os
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable
import logging
logger = logging.getLogger(__name__)


class RingCentralCSV:
	'''
	Helper class to handle the RingCentral address book file.
	'''
	def __init__(self, csv_in=None, csv_path_out="results"):
		self.csv_in = csv_in
		self.csv_path_out = csv_path_out

		if os.path.exists(self.csv_path_out):
			pass
		else:
			print(f"/{self.csv_path_out} does not exist, creating...")
			os.makedirs(csv_path_out, exist_ok=True)


	def checker(self, csv_in_path: str, required_headers: Iterable[str] = ("First Name", "Surname")) -> list[dict]:
		'''
		Check the file until the real header row is found, then parse into list dict. 
		Returns list dict, sets self.fieldnames.
		
		required_headers: headers that MUST appear in the header row
		'''
		path = Path(csv_in_path).expanduser()
		logger.info("Reading CSV: %s", path)
		
		if not path.exists():
			logger.error("CSV not found: %s", path)
			raise FileNotFoundError(f"CSV not found: {path}")

		required = {str(h or "").strip() for h in required_headers}
		logger.debug("Required headers: %s", sorted(required))

		with path.open("r", newline="", encoding="utf-8-sig") as f:
			start = f.read(2048)
			if not start.strip():
				self.fieldnames = []
				logger.warning("CSV is empty (no headers): %s", path)
				raise ValueError("CSV is empty (no headers).")

			f.seek(0)

			while True:
				pos = f.tell()
				line = f.readline()

				if line == "":
					logger.error("Header row not found in %s", path)
					raise ValueError(f"Could not find header row containing {sorted(required)} in file: {path}")

				row = next(csv.reader([line]))
				row_set = {str(cell or "").strip().lstrip("\ufeff") for cell in row}

				if required.issubset(row_set):
					logger.info("Header found at byte offset %s in %s", pos, path)
					f.seek(pos)

					reader = csv.DictReader(f, restkey="__extra__", restval="")
					self.fieldnames = reader.fieldnames or []
					logger.debug("Detected fieldnames: %s", self.fieldnames)

					data = list(reader)
					
					for row in data:
						row.pop("__extra__", None)

					logger.info("Loaded %d data rows from %s", len(data), path)
					return data


	def normalise_row(self, raw_row: dict) -> dict:
		"""
		Take raw user input (dict[str,str]) and return a cleaned row dict.
		Raises ValueError with a useful message on the first invalid field.
		"""
		if not getattr(self, "fieldnames", None):
			raise ValueError("No fieldnames loaded.")

		cleaned = {k: "" for k in self.fieldnames}
		for key in self.fieldnames:
			raw_text = (raw_row.get(key, "") or "").strip()
			cleaned[key] = self.field_formatter(key, raw_text)
		return cleaned

	def append_row(self, csv_data: list[dict], raw_row: dict) -> dict:
		"""
		Validate + append one row to csv_data. Returns the appended cleaned row.
		"""
		cleaned = self.normalise_row(raw_row)
		logger.debug("Appending row (pre-validate)")

		# Check duplicates within the new row itself
		new_nums = []
		for k, v in cleaned.items():
			if self._is_phone_field(k):
				n = (v or "").strip()
				if n:
					new_nums.append((k, n))
		seen_local = {}
		for field, num in new_nums:
			if num in seen_local:
				
				raise ValueError(f"Duplicate number inside new row: {num} in {seen_local[num]} and {field}")
			seen_local[num] = field

		# Check duplicates against existing data
		self.assert_no_duplicate_numbers(csv_data + [cleaned])

		csv_data.append(cleaned)
		logger.info("Row appended successfully. New row count: %d", len(csv_data))
		return cleaned


	def writer(self, fieldnames: list[str], csv_data: list[dict]) -> Path:
		'''
		Accepts incoming csv data after appended data is added to the new list. 
		Writes a new csv file with date stamp.
		'''
		
		file_date = datetime.now().strftime("%Y%m%d-%H%M")

		out_dir = Path(self.csv_path_out).expanduser()
		out_dir.mkdir(parents=True, exist_ok=True)

		out_path = out_dir / f"AddressBook-{file_date}.csv"

		with out_path.open("w", newline="", encoding="utf-8") as f:
			writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
			writer.writeheader()
			writer.writerows(csv_data)

		return out_path

		

	def _is_phone_field(self, field: str) -> bool:
		PHONE_FIELDS = {"home number", "business number", "mobile number", "company main number"}
		return field.strip().casefold() in PHONE_FIELDS

	def find_duplicate_numbers(self, rows: list[dict]) -> list[tuple[str, int, str, int, str]]:
		"""
		Returns duplicates as tuples:
		(number, first_row_index, first_field, dup_row_index, dup_field)
		Row indexes are 0-based for your csv_data list.
		"""
		logger.debug("Scanning $d rows for duplicate numbers", len(rows))

		seen: dict[str, tuple[int, str]] = {}
		dups: list[tuple[str, int, str, int, str]] = []

		for i, row in enumerate(rows):
			for key, value in row.items():
				if not self._is_phone_field(key):
					continue
				number = (value or "").strip()
				if not number:
					continue

				if number in seen:
					first_i, first_field = seen[number]
					dups.append((number, first_i, first_field, i, key))
				else:
					seen[number] = (i, key)
		logger.info("Duplicate scan complete: $d duplicates found", len(dups))
		return dups

	def format_duplicate_report(self, rows: list[dict], limit: int = 10) -> str:
		dups = self.find_duplicate_numbers(rows)
		if not dups:
			return ""

		lines = []
		for number, first_i, first_field, dup_i, dup_field in dups[:limit]:
			lines.append(f"{number}: row {first_i+1} ({first_field}) and row {dup_i+1} ({dup_field})")

		more = "" if len(dups) <= limit else f"\n…and {len(dups)-limit} more."
		return "Duplicate phone numbers detected:\n" + "\n".join(lines) + more

	def assert_no_duplicate_numbers(self, rows: list[dict]) -> None:
		"""
		Raise ValueError if any phone number appears more than once.
		"""
		dups = self.find_duplicate_numbers(rows)
		if not dups:
			return
		raise ValueError(self.format_duplicate_report(rows))


	@staticmethod
	def field_formatter(fieldnames, value: str) -> str:
		"""
		Automatically normalises entries based on field header. 
		
		Names:
		  Strings only, no numbers. 

		Email:
		  Email only

		Job Title/Company Name:
		  Strings only, no numbers.

		Mobiles:
		  04XXXXXXXX      -> +614XXXXXXXX
		  614XXXXXXXX     -> +614XXXXXXXX
		  +614XXXXXXXX    -> +614XXXXXXXX

		Landlines:
		  0[2378]XXXXXXXX -> +61[2378]XXXXXXXX
		  +61[2378]XXXXXXXX stays as-is

		Service numbers:
		  13XXXX          -> +6113XXXX
		  1300XXXXXX      -> +611300XXXXXX
		  1800XXXXXX      -> +611800XXXXXX
		"""

		field = fieldnames.strip().casefold()
		raw_value = value.strip()

		# If nothing is entered just return nothing.
		if raw_value == "":
			return ""

		# --- Names ---
		if field in {"first name", "surname"}:
			if not re.fullmatch(r"[A-Za-z]+(?:[ '\-][A-Za-z]+)*", raw_value):
				raise ValueError("Names must contain letters only (spaces, hyphens, apostrophes allowed)")
			return raw_value.title()

		# --- Job title / Company ---
		if field in {"job title", "company"}:
			if not re.fullmatch(r"[A-Za-z]+(?:[ '\-][A-Za-z]+)*", raw_value):
				raise ValueError("Names must contain letters only (spaces, hyphens, apostrophes allowed)")
			return raw_value.title()

		# --- Email --- 
		if field == "email":
			email = raw_value.lower()
			if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
				raise ValueError("Email doesn't look valid (expected name@domain.tld)")
			return email

		# --- Phone numbers (AU) ---
		if field in {"home number", "business number", "mobile number", "company main number"}:
			number_cleaned = re.sub(r"[^\d+]", "", raw_value)

			# If starts with +, validate then return
			if number_cleaned.startswith("+"):
				if re.fullmatch(r"\+614\d{8}", number_cleaned):
					return number_cleaned
				if re.fullmatch(r"\+61[2378]\d{8}", number_cleaned):
					return number_cleaned
				if re.fullmatch(r"\+6113\d{4}", number_cleaned) or re.fullmatch(r"\+611(300|800)\d{6}", number_cleaned):
					return number_cleaned
				raise ValueError("Expected Australian number in E.164 format (e.g. +614..., +612..., +611300...)")

			# Digits only
			number_cleaned = re.sub(r"\D", "", number_cleaned)

			# Mobile
			if re.fullmatch(r"04\d{8}", number_cleaned):
				return "+61" + number_cleaned[1:]
			if re.fullmatch(r"614\d{8}", number_cleaned):
				return "+" + number_cleaned

			# Landline
			if re.fullmatch(r"0[2378]\d{8}", number_cleaned):
				return "+61" + number_cleaned[1:]
			if re.fullmatch(r"61[2378]\d{8}", number_cleaned):
				return "+" + number_cleaned

			# Service numbers
			if re.fullmatch(r"13\d{4}", number_cleaned):
				return "+61" + number_cleaned
			if re.fullmatch(r"1300\d{6}", number_cleaned) or re.fullmatch(r"1800\d{6}", number_cleaned):
				return "+61" + number_cleaned
			if re.fullmatch(r"6113\d{4}", number_cleaned) or re.fullmatch(r"61(300|800)\d{6}", number_cleaned):
				return "+" + number_cleaned

			raise ValueError("Not a valid AU phone number (mobile, landline(must include area code(08,07,03...)), or 13/1300/1800)")

		# --- Source / External ID ---
		if field in {"source", "external id"}:
			return raw_value