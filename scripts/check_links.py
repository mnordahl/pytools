#!/usr/bin/env python

# Dependency check
REQUIRED_MODULES = ["requests", "tqdm"]

missing = []
for mod in REQUIRED_MODULES:
    try:
        __import__(mod)
    except ImportError:
        missing.append(mod)

if missing:
    print("\nMissing required modules:", ", ".join(missing))
    print("Install them using pip:\n")
    print(f"    pip install {' '.join(missing)}")
    exit(1)


import os
import re
import csv
import json
import argparse
from html.parser import HTMLParser
from urllib.parse import urlparse, urljoin
import requests
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from collections import defaultdict


# HTML parser to extract hrefs
class LinkExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            for attr, val in attrs:
                if attr.lower() == "href":
                    self.links.add(val)


# Recursively find HTML files
def find_html_files(directory):
    html_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(".html"):
                html_files.append(os.path.join(root, file))
    return html_files


# Extract links and resolve them
def extract_links(files, base_url=None):
    absolute_links = set()
    relative_or_invalid_links = set()
    link_origins = {}

    for filepath in files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                parser = LinkExtractor()
                parser.feed(content)
                rel_base = ""
                if base_url:
                    rel_path = os.path.relpath(filepath)
                    rel_base = urljoin(base_url + "/", rel_path.replace("\\", "/"))
                for link in parser.links:
                    if base_url and not urlparse(link).scheme:
                        resolved = urljoin(rel_base, link)
                        absolute_links.add(resolved)
                        link_origins[resolved] = filepath
                    else:
                        parsed = urlparse(link)
                        if parsed.scheme in ("http", "https"):
                            absolute_links.add(link)
                            link_origins[link] = filepath
                        else:
                            relative_or_invalid_links.add(link)
        except Exception as e:
            print(f"Error reading {filepath}: {e}")

    return absolute_links, relative_or_invalid_links, link_origins


# Function to check a single link
def check_link(url, timeout, user_agent):
    try:
        headers = {"User-Agent": user_agent} if user_agent else {}
        response = requests.head(
            url, allow_redirects=True, timeout=timeout, headers=headers
        )
        return url, response.status_code, (200 <= response.status_code < 400)
    except Exception as e:
        return url, None, False


# Check links using multithreading
def check_links(links, timeout, user_agent, max_workers=10):
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(check_link, url, timeout, user_agent): url for url in links
        }
        for future in tqdm(
            as_completed(future_to_url), total=len(links), desc="Checking URLs"
        ):
            url, status_code, ok = future.result()
            results[url] = {"ok": ok, "status_code": status_code}
    return results


def group_links_by_file(results, link_origins, years_back=5):
    current_year = datetime.now().year
    old_years = {str(y) for y in range(current_year - years_back, current_year)}

    grouped = defaultdict(lambda: {"ok": [], "fail": [], "old": []})

    for url, info in results.items():
        source_file = link_origins.get(url, "UNKNOWN")
        status = "ok" if info.get("ok") else "fail"

        grouped[source_file][status].append(url)

        # Check for old year markers in URL
        found_years = re.findall(r"\b(20\d{2})\b", url)
        if any(y in old_years for y in found_years):
            grouped[source_file]["old"].append(url)

    return grouped


# Save results to file
def save_results(file_summary, format, output_file):
    with open(output_file, "w", encoding="utf-8", newline="") as f:
        if format == "json":
            json.dump(file_summary, f, indent=2)
        elif format == "csv":
            writer = csv.writer(f)
            writer.writerow(["source_file", "status", "url"])
            for filepath, categories in file_summary.items():
                for status, urls in categories.items():
                    for url in urls:
                        writer.writerow([filepath, status, url])
        else:  # plain text
            add_newline = False
            for filepath, categories in file_summary.items():
                if add_newline:
                    f.write("\n")
                else:
                    add_newline = True
                f.write(f"{filepath}\n")
                for status, urls in categories.items():
                    tag = status.upper()
                    for url in urls:
                        f.write(f"[{tag}] ".rjust(8) + f"{url}\n")


def main():
    parser = argparse.ArgumentParser(description="Check links in HTML files.")
    parser.add_argument("directory", help="Directory to scan")
    parser.add_argument("--base-url", help="Base URL to resolve relative links")
    parser.add_argument("-o", "--output", help="Output file to save results")
    parser.add_argument(
        "--format",
        choices=["text", "json", "csv"],
        default="text",
        help="Output format",
    )
    parser.add_argument(
        "--timeout", type=int, default=5, help="Request timeout in seconds"
    )
    parser.add_argument("--max", type=int, help="Maximum number of links to check")
    parser.add_argument("--exclude", help="Regex to exclude matching links")
    parser.add_argument("--user-agent", help="Custom User-Agent string")
    parser.add_argument("--verbose", action="store_true", help="Show detailed info")
    parser.add_argument(
        "--fail-only", action="store_true", help="Only show failed links"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Extract links but don't check them"
    )
    args = parser.parse_args()

    print(f"Scanning directory: {args.directory}")
    html_files = find_html_files(args.directory)
    absolute_links, relative_links, link_origins = extract_links(
        html_files, args.base_url
    )

    if args.exclude:
        pattern = re.compile(args.exclude)
        absolute_links = {url for url in absolute_links if not pattern.search(url)}

    if args.max:
        absolute_links = set(list(absolute_links)[: args.max])

    print(
        f"\nFound {len(absolute_links)} absolute links, "
        f"{len(relative_links)} relative/unparseable links."
    )

    if args.dry_run:
        print("Dry-run mode: skipping link checking.")
        results = {}
    else:
        results = check_links(absolute_links, args.timeout, args.user_agent)

    file_summary = group_links_by_file(results, link_origins)
    print("\n=== Link Status ===")
    for filepath, categories in file_summary.items():
        print(f"\n{filepath}")
        for label, urls in categories.items():
            tag = label.upper()
            for url in urls:
                print(f"[{tag}]".rjust(8) + f" {url}")

    if relative_links:
        print("\n=== Relative or Unparseable Links ===")
        for url in sorted(relative_links):
            print(f"[??] {url}")

    if args.output:
        print(f"\nSaving results to: {args.output} ({args.format})")
        save_results(file_summary, args.format, args.output)


if __name__ == "__main__":
    main()
