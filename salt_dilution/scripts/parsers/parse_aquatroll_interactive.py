import csv
import os
import re
from html.parser import HTMLParser

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

def parse_isi_file(html_file_path, output_dir):
    parser = MyHTMLParser()
    metadataGroups = {}
    dataTables = []

    os.makedirs(output_dir, exist_ok=True)

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

    # Write metadata CSV
    meta_out = os.path.join(output_dir, "metadata.csv")
    with open(meta_out, 'w', newline='', encoding='utf-8') as meta_file:
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

    # Construct output filename
    log_name = extract_metadata_value(metadataGroups, "LogProperties", "Name")
    serial_number = extract_metadata_value(metadataGroups, "InstrumentProperties", "SerialNumber")
    output_filename = f"{sanitize_filename(log_name)}_{sanitize_filename(serial_number)}.csv"
    data_out = os.path.join(output_dir, output_filename)

    # Write data CSV
    with open(data_out, 'w', newline='', encoding='utf-8') as out_file:
        writer = csv.writer(out_file)
        for i, table in enumerate(dataTables):
            if i > 0:
                writer.writerow([])  # Blank row between tables
            headers = [h['Name'] for h in table['Headers']]
            writer.writerow(headers)
            for row in table['Values']:
                writer.writerow(row)

    print(f"\n✅ Done.")
    print(f"📄 Metadata saved to: {meta_out}")
    print(f"📊 Data saved to:     {data_out}")

def main():
    html_path = input("Enter path to HTML file: ").strip()
    output_dir = input("Enter output directory (will be created if needed): ").strip()
    parse_isi_file(html_path, output_dir)

if __name__ == "__main__":
    main()
