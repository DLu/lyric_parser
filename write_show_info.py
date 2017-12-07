from util import get_songs, all_sections
import yaml, os, collections, pprint, sys

config = yaml.load(open(sys.argv[1]+'.yaml'))
show_info = {'songs': {}}
if 'song_keys' not in config:
    config['song_keys'] = {}
if 'char_keys' not in config:
    config['char_keys'] = {}
try:
    for filename, song in sorted(get_songs(sys.argv[1]).items()):
        if filename not in config.get('song_keys', {}):
            x = raw_input(filename + ' abbrev? ')
            config['song_keys'][filename] = x
        key = config['song_keys'][filename]
        D = {}
        D['title'] = song['title']
        D['order'] = song['track_no']
        D['parts'] = collections.defaultdict(int)
        for section in all_sections(song['lyrics']):
            if 'header' not in section or 'characters' not in section['header']:
                continue
            for ch in section['header']['characters']:
                if ch in config.get('ignore_chars', []):
                    continue
                if ch not in config.get('char_keys', {}):
                    x = raw_input(ch + ' abbrev? ')
                    config['char_keys'][ch] = x
                ckey = config['char_keys'][ch]
                for line in section['lines']:
                    D['parts'][ckey]+=len(line.split())
        D['parts'] = dict(D['parts'])
        show_info['songs'][key] = D
    show_info['chars'] = {}
    for k,v in config['char_keys'].iteritems():
        show_info['chars'][v]=k.title()
    show_info['title'] = config['title']
finally:
    yaml.dump(config, open(sys.argv[1]+'.yaml', 'w'))
print yaml.dump(show_info)
yaml.dump(show_info, open('/home/dlu/Desktop/Hamiltunes/shows/' + sys.argv[1] + '.yaml', 'w'))
