import yaml, os, collections, pprint, sys

missing_headers = 0
missing_chars = 0
total = 0

def analyze_section(section):
    global total, missing_chars, missing_headers
    total +=1
    if 'header' not in section:
        print "No header"
        print section
        print
        missing_headers += 1
    elif 'characters' not in section['header'] and len(section.get('lines', []))>0:
        print 'No chars'
        print section
        print
        missing_chars += 1

folder = sys.argv[1]
for filename in sorted(os.listdir(folder)):
    print filename
    lyrics = yaml.load(open(os.path.join(folder, filename)))['lyrics']
    for section in lyrics:
        if 'stage_direction' in section:
            continue
        elif 'simultaneous' in section:
            for s_list in section['simultaneous']:
                for s2 in s_list:
                    analyze_section(s2)
        else:
            analyze_section(section)
print '%d missing headers (%.2f)'%(missing_headers, float(missing_headers)/total)
print '%d missing chars (%.2f)'%(missing_chars, float(missing_chars)/total)