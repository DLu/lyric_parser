from util import get_songs, all_sections
import yaml, os, collections, pprint, sys

OVERALL = collections.defaultdict(int)

cfg = yaml.load(open(sys.argv[1] + '.yaml'))

for filename, song in sorted(get_songs(sys.argv[1]).items()):
    print filename
    D = collections.defaultdict(int)
    for section in all_sections(song['lyrics']):
        if 'header' not in section or 'characters' not in section['header']:
            continue
        for ch in section['header']['characters']:
            for line in section['lines']:
                D[ch]+=len(line.split())
                OVERALL[ch] += len(line.split())

    for name, count in sorted(D.items(), key=lambda x: -x[1]):
        if name in cfg.get('ignore_chars', []):
            continue
        print '%5s %s'%(str(count), name)
    print len(D)

for name, count in sorted(OVERALL.items(), key=lambda x: -x[1]):
    if name in cfg.get('ignore_chars', []):
        continue
    print '%5s %s'%(str(count), name)
print len(OVERALL)
