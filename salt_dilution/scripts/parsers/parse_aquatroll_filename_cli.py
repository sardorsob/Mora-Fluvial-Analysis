from pathlib import Path
import argparse
import os
import re
import csv
from html.parser import HTMLParser

class MyHTMLParser(HTMLParser):
    def FeedLine(self, line, reset):
        if reset:
            self.startStack = []
            self.endStack = []
            self.elements = []
        self.feed(line)

    def __init__(self):
        super().__init__()
        self.current_group = None
        self.current_property = None
        self.capture_serial = False
        self.serial_number = None

    def handle_starttag(self, tag, attrs):
        self.startStack.append(tag)
        self.elements.append({})
        if len(attrs) > 0:
            self.elements[-1]["attrs"] = attrs

        attrs_dict = dict(attrs)

        if tag == "td" and "isi-group-member" in attrs_dict:
            self.current_group = attrs_dict["isi-group-member"]
            if "isi-property" in attrs_dict:
                self.current_property = attrs_dict["isi-property"]

        if tag == "span" and "isi-value" in attrs_dict and self.current_property == "SerialNumber":
            self.capture_serial = True

    def handle_endtag(self, tag):
        self.endStack.append(tag)
        if tag == "td":
            self.current_group = None
            self.current_property = None

    def handle_data(self, data):
        if data.strip() == "" or data.strip().rstrip() == "=":
            return
        if len(self.elements) < 1:
            return
        self.elements[-1]["data"] = data

        if (
            self.capture_serial
            and self.current_group == "InstrumentProperties"
            and self.current_property == "SerialNumber"
        ):
            self.serial_number = data.strip()
            self.capture_serial = False

def GetAttr(attrs, ofType):
    for attr in attrs:
        if attr[0] == ofType:
            return attr
    return None

def ContainsAttr(attrs, ofType):
    return GetAttr(attrs, ofType) is not None

def sanitize_filename(s):
    return re.sub(r"[^A-Za-z0-9._-]", "_", s.strip())

def extract_metadata_value(metadataGroups, group_name, property_name):
    group = metadataGroups.get(group_name)
    if not group:
        return "Unknown"
    val = group.get(property_name)
    if isinstance(val, dict) and "Value" in val:
        return val["Value"]
    return "Unknown"

def parse_isi_file(html_file_path):
    parser = MyHTMLParser()
    metadataGroups = {}
    dataTables = []

    with open(html_file_path, "r", encoding="utf-8") as fptr:
        for line in fptr:
            parser.FeedLine(line, True)
            if "body" in parser.startStack:
                break

        resetLine = True
        for line in fptr:
            parser.FeedLine(line, resetLine)
            resetLine = True

            if "tr" not in parser.startStack:
                continue
            if "tr" not in parser.endStack:
                resetLine = False
                continue
            if len(parser.elements) < 1 or "attrs" not in parser.elements[0]:
                continue

            startIndex = parser.startStack.index("tr")

            for element in parser.elements[startIndex:]:
                if "attrs" not in element:
                    continue

                if ContainsAttr(element["attrs"], "isi-group"):
                    attr = GetAttr(element["attrs"], "isi-group")
                    metadataGroups[attr[1]] = {"Name": attr[1]}

                elif ContainsAttr(element["attrs"], "isi-group-member"):
                    attr = GetAttr(element["attrs"], "isi-group-member")
                    metaData = parser.elements[1]["attrs"]
                    groupName = GetAttr(metaData, "isi-group-member")[1]

                    isiProperty = GetAttr(element["attrs"], "isi-property")
                    if isiProperty is not None:
                        label = parser.elements[2]["data"]
                        value = parser.elements[3]["data"]
                        metadataGroups[groupName][isiProperty[1]] = {
                            "Label": label,
                            "Value": value,
                        }

                elif ContainsAttr(element["attrs"], "isi-data-table"):
                    dataTables.append({"Headers": [], "Values": []})

                elif ContainsAttr(element["attrs"], "isi-data-column-header"):
                    hold = {"Name": element["data"]}
                    for attr in element:
                        hold[attr[0]] = attr[1]
                    dataTables[-1]["Headers"].append(hold)

                elif ContainsAttr(element["attrs"], "isi-data-row"):
                    hold = []
                    for element in parser.elements:
                        if "attrs" in element and ContainsAttr(
                            element["attrs"], "isi-data-row"
                        ):
                            continue
                        elif "data" in element:
                            hold.append(element["data"])
                        else:
                            hold.append(" ")
                    dataTables[-1]["Values"].append(hold)

    return metadataGroups, dataTables, parser.serial_number

def extract_filename_parts(source_file, metadata, serial_number):
    filename = os.path.basename(source_file)

    # Try to extract timestamp from filename
    match_live = re.search(r"LiveReadings_(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})", filename)
    match_log = re.search(r"Log_(\d{4})-(\d{2})-(\d{2})", filename)

    if match_live:
        y, m, d, H, M, S = match_live.groups()
        timestamp = f"{y[2:]}{m}{d}_{H}{M}{S}"
        base_name = f"{timestamp}_{sanitize_filename(serial_number or 'Unknown')}"
    elif match_log:
        y, m, d = match_log.groups()
        date_part = f"{y}{m}{d}"
        log_name = extract_metadata_value(metadata, "LogProperties", "Name")
        trial = sanitize_filename(log_name.split("_")[-1]) if "_" in log_name else "Unknown"
        base_name = f"{date_part}_{trial}_{sanitize_filename(serial_number or 'Unknown')}"
    else:
        base_name = f"unknown_{sanitize_filename(serial_number or 'Unknown')}"

    return base_name

def save_outputs(metadata, dataTables, output_dir, source_file, serial_number, dry_run=False):
    os.makedirs(output_dir, exist_ok=True)
    base_name = extract_filename_parts(source_file, metadata, serial_number)
    data_path = os.path.join(output_dir, f"{base_name}.csv")
    meta_path = os.path.join(output_dir, f"{base_name}_metadata.csv")

    if dry_run:
        print(f"💡 DRY RUN: Would save data to:     {data_path}")
        print(f"💡 DRY RUN: Would save metadata to: {meta_path}")
        return

    with open(data_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for i, table in enumerate(dataTables):
            if i > 0:
                writer.writerow([])
            headers = [h["Name"] for h in table["Headers"]]
            writer.writerow(headers)
            for row in table["Values"]:
                writer.writerow(row)

    with open(meta_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Group", "Property", "Label", "Value"])
        for group, props in metadata.items():
            for key, val in props.items():
                if key == "Name":
                    continue
                if key == "Notes":
                    for note in val:
                        for nk, nv in note.items():
                            writer.writerow([group, f"Note-{nk}", "", nv])
                else:
                    writer.writerow([group, key, val["Label"], val["Value"]])

    print(f"✅ Saved data to:     {data_path}")
    print(f"✅ Saved metadata to: {meta_path}")

def main():
    parser = argparse.ArgumentParser(description="Parse ISI HTML logs and live readings.")
    parser.add_argument("html_dir", help="Path to folder with HTML files")
    parser.add_argument("-o", "--output", default=str(Path(__file__).resolve().parents[2] / "data" / "processed"), help="Output folder")
    parser.add_argument("--dry-run", action="store_true", help="Only preview output paths")
    args = parser.parse_args()

    if not os.path.isdir(args.html_dir):
        print(f"❌ Not a valid directory: {args.html_dir}")
        return

    html_files = [
        os.path.join(args.html_dir, f)
        for f in os.listdir(args.html_dir)
        if f.lower().endswith(".html")
    ]

    for html_file in html_files:
        metadata, tables, serial_number = parse_isi_file(html_file)
        save_outputs(metadata, tables, args.output, html_file, serial_number, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
