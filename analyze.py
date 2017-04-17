from util import get_songs, all_sections
import yaml, os, collections, pprint, sys

D = collections.defaultdict(int)
config = yaml.load(open(sys.argv[1]+'.yaml'))
for filename, song in get_songs(sys.argv[1]).iteritems():
    for section in all_sections(song['lyrics']):
        if 'header' not in section or 'characters' not in section['header']:
            continue
        for ch in section['header']['characters']:
            if ch in config.get('ignore_chars', []):
                continue
            for line in section['lines']:
                D[ch]+=len(line.split())

for name, count in sorted(D.items(), key=lambda x: -x[1]):
    print '%5s %s'%(str(count), name)
print len(D)