import yaml, os

def get_songs(folder):
    songs = {}
    for filename in sorted(os.listdir(folder)):
        lyrics = yaml.load(open(os.path.join(folder, filename)))
        songs[filename] = lyrics
    return songs

def all_sections(lyrics):
    for section in lyrics:
        if 'stage_direction' in section:
            continue
        elif 'simultaneous' in section:
            for s_list in section['simultaneous']:
                for s2 in s_list:
                    yield s2
        else:
            yield section
