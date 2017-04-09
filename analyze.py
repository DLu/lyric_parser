import yaml, os, collections, pprint, sys

D = collections.defaultdict(int)

def analyze_section(section):
    if 'header' not in section:
        return
    for ch in section['header']['characters']:
        D[ch]+=len(section['lines'])

folder = sys.argv[1]
for filename in sorted(os.listdir(folder)):
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
    

for name, count in sorted(D.items(), key=lambda x: -x[1]):
    print '%5s %s'%(str(count), name)
print len(D)