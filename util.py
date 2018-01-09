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

def section_map(lyrics, function):
    replacements = []
    for section in lyrics:
        if 'stage_direction' in section:
            replacements.append(section)
        elif 'simultaneous' in section:
            ss = []
            for s_list in section['simultaneous']:
                for s2 in s_list:
                    ss.append(function(s2))
            replacements.append({'simultaneous': ss})
        else:
            replacements += function(section)

    return replacements
