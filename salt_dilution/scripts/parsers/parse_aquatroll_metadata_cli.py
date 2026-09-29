from pathlib import Path
import argparse
import os
import csv
import re
from html.parser import HTMLParser

def parse_meta_tags(html_file_path):
    meta_info = {}
    meta_re = re.compile(r'<meta\s+name="([^"]+)"\s+content="([^"]+)"', re.IGNORECASE)
    with open(html_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if '<meta' in line.lower():
                for match in meta_re.finditer(line):
                    meta_info[match.group(1)] = match.group(2)
            if '</head>' in line.lower():
                break
    return meta_info


class MyHTMLParser(HTMLParser):
    def FeedLine(self, line, reset):
        if reset:
            self.startStack = []
            self.endStack = []
            self.elements = []
        self.feed(line)

    def handle_starttag(self, tag, attrs):
        self.startStack.append(tag)
        self.elements.append({})
        if len(attrs) > 0:
            self.elements[-1]["attrs"] = attrs

    def handle_endtag(self, tag):
        self.endStack.append(tag)

    def handle_data(self, data):
        if data.strip() == "" or data.strip().rstrip() == "=":
            return
        if len(self.elements) < 1:
            return
        self.elements[-1]["data"] = data

def GetAttr(attrs, ofType):
    for attr in attrs:
        if attr[0] == ofType:
            return attr
    return None

def ContainsAttr(attrs, ofType):
    return GetAttr(attrs, ofType) is not None

def extract_metadata_value(metadataGroups, group_name, property_name):
    group = metadataGroups.get(group_name)
    if not group:
        return "Unknown"
    val = group.get(property_name)
    if isinstance(val, dict) and "Value" in val:
        return val["Value"]
    return "Unknown"

def sanitize_filename(s):
    return re.sub(r'[^A-Za-z0-9._-]', '_', s.strip())

def parse_isi_file(html_file_path):
    parser = MyHTMLParser()
    metadataGroups = {}
    dataTables = []

    with open(html_file_path, 'r', encoding='utf-8') as fptr:
        for line in fptr:
            parser.FeedLine(line, True)
            if 'body' in parser.startStack:
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
            if len(parser.elements) < 1 or 'attrs' not in parser.elements[0]:
                continue

            startIndex = parser.startStack.index('tr')

            for element in parser.elements[startIndex:]:
                if 'attrs' not in element:
                    continue

                if ContainsAttr(element['attrs'], 'isi-group'):
                    attr = GetAttr(element['attrs'], 'isi-group')
                    metadataGroups[attr[1]] = {"Name": attr[1]}

                elif ContainsAttr(element['attrs'], 'isi-group-member'):
                    attr = GetAttr(element['attrs'], 'isi-group-member')
                    metaData = parser.elements[1]['attrs']
                    groupName = GetAttr(metaData, 'isi-group-member')[1]

                    isiProperty = GetAttr(element['attrs'], 'isi-property')
                    if isiProperty is not None:
                        label = parser.elements[2]['data']
                        value = parser.elements[3]['data']
                        metadataGroups[groupName][isiProperty[1]] = {'Label': label, 'Value': value}

                elif ContainsAttr(element['attrs'], 'isi-data-table'):
                    dataTables.append({'Headers': [], 'Values': []})

                elif ContainsAttr(element['attrs'], 'isi-data-column-header'):
                    hold = {'Name': element['data']}
                    for attr in element:
                        hold[attr[0]] = attr[1]
                    dataTables[-1]['Headers'].append(hold)

                elif ContainsAttr(element['attrs'], 'isi-data-row'):
                    hold = []
                    for element in parser.elements:
                        if 'attrs' in element and ContainsAttr(element['attrs'], 'isi-data-row'):
                            continue
                        elif 'data' in element:
                            hold.append(element['data'])
                        else:
                            hold.append(' ')
                    dataTables[-1]['Values'].append(hold)

    return metadataGroups, dataTables

def save_outputs(metadataGroups, dataTables, output_dir, source_file, meta_info=None, dry_run=False):
    os.makedirs(output_dir, exist_ok=True)

    base_name = "unknown"

    if meta_info and meta_info.get("isi-report-type", "").lower() == "livereadings":
        csv_name = meta_info.get("isi-csv-file-name", "")
        live_reading_pattern = re.match(
            r"VuSitu_LiveReadings_(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})_(.+)\.csv", csv_name
        )
        if live_reading_pattern:
            date_part = live_reading_pattern.group(1).replace("-", "")
            time_part = live_reading_pattern.group(2).replace("-", "")
            # serial_number = extract_metadata_value(metadataGroups, "InstrumentProperties", "SerialNumber") - this ain't right
            device_part = live_reading_pattern.group(3)
            base_name = f"{date_part}_{time_part}_{sanitize_filename(device_part)}"
        else:
            base_name = "unknown_livereading"
    else:
        log_name_raw = extract_metadata_value(metadataGroups, "LogProperties", "Name")
        serial_number = extract_metadata_value(metadataGroups, "InstrumentProperties", "SerialNumber")

        log_pattern = re.match(r"Log_(\d{4})-(\d{2})-(\d{2})(.*)", log_name_raw)
        if log_pattern:
            date_part = f"{log_pattern.group(1)}{log_pattern.group(2)}{log_pattern.group(3)}"
            trial_part = log_pattern.group(4).strip("_- ")
        else:
            date_part = "unknown_date"
            trial_part = sanitize_filename(log_name_raw)

        serial_clean = sanitize_filename(serial_number)
        trial_clean = sanitize_filename(trial_part)

        base_name = f"{date_part}_{trial_clean}_{serial_clean}"


    # Extract fields from metadata

    meta_path = os.path.join(output_dir, f"{base_name}_metadata.csv")
    data_path = os.path.join(output_dir, f"{base_name}.csv")

    if dry_run:
        print(f"DRY RUN: Would save metadata to: {meta_path}")
        print(f"DRY RUN: Would save data to:     {data_path}")
        return

    # Save metadata CSV
    with open(meta_path, 'w', newline='', encoding='utf-8') as meta_file:
        writer = csv.writer(meta_file)
        writer.writerow(['Group', 'Property', 'Label', 'Value'])
        for group, props in metadataGroups.items():
            for key, val in props.items():
                if key == 'Name':
                    continue
                if key == 'Notes':
                    for note in val:
                        for note_key, note_val in note.items():
                            writer.writerow([group, f'Note-{note_key}', '', note_val])
                else:
                    writer.writerow([group, key, val['Label'], val['Value']])

    # Save data tables CSV
    with open(data_path, 'w', newline='', encoding='utf-8') as out_file:
        writer = csv.writer(out_file)
        for i, table in enumerate(dataTables):
            if i > 0:
                writer.writerow([])
            headers = [h['Name'] for h in table['Headers']]
            writer.writerow(headers)
            for row in table['Values']:
                writer.writerow(row)

    print(f"✅ Parsed {os.path.basename(source_file)}")
    print(f"   ├─ Metadata: {meta_path}")
    print(f"   └─ Data:     {data_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Batch ISI HTML Parser - process all .html files in a directory."
    )
    parser.add_argument("html_dir", help="Path to the directory containing HTML files.")
    parser.add_argument("-o", "--output", default=str(Path(__file__).resolve().parents[2] / "data" / "processed"), help="Output directory (default: data/examples)")
    parser.add_argument("--dry-run", action="store_true", help="Preview output filenames without saving files.")

    args = parser.parse_args()

    if not os.path.isdir(args.html_dir):
        print(f"❌ Error: '{args.html_dir}' is not a valid directory.")
        return

    html_files = [
        os.path.join(args.html_dir, f)
        for f in os.listdir(args.html_dir)
        if f.lower().endswith('.html') and os.path.isfile(os.path.join(args.html_dir, f))
    ]

    if not html_files:
        print(f"⚠️ No HTML files found in '{args.html_dir}'")
        return

    for html_file in html_files:
        meta_info = parse_meta_tags(html_file)
        metadata, tables = parse_isi_file(html_file)
        save_outputs(metadata, tables, args.output, html_file, meta_info=meta_info)

if __name__ == "__main__":
    import argparse
    main()
