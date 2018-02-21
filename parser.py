#!/usr/bin/python
from bs4 import BeautifulSoup
import re
import yaml
import collections
from util import all_sections, section_map, get_songs

# Step 1: Parse Tables
# Step 2: Parse Character Lines

END_TABLE = '</table>'

def split_by_tables(s):
    pieces = []
    while '<table' in s:
        i = s.index('<table')
        i2 = s.index(END_TABLE, i) + len(END_TABLE)
        first = s[:i]
        pieces.append(first)
        table_s = s[i:i2]
        table = BeautifulSoup(table_s, 'html.parser')
        cols = []
        for row in table.find_all('tr'):
            for i, cell in enumerate(row.find_all('td')):
                if i >= len(cols):
                    cols.append([])
                cols[i].append(cell.text)
        pieces.append(['\n'.join(x) for x in cols])
        s = s[i2 + 1:]
    if len(s) > 0:
        pieces.append(s)
    return pieces


CHAR_LINE = re.compile('\[([^\]:]+):?\]')
LOWERCASE = re.compile('[a-z]')
PAREN_SECTION = re.compile('\(([^\)]+)\)')
STAGE_DIRECTION = [
    re.compile('\(<i>([^<]+)</i>\)'),
    re.compile('<i>\(([^\)]+)\)</i>'),
    re.compile('\(([^\)]+)\)'),
    re.compile('<b>\[([^\]]+)\]</b>'),
    re.compile('<i>\[([^\]]+)\]</i>'),
]
PARENTHETICAL = re.compile('(.*)\((.*)\)')


def get_element(tag, subtype, attribute, value):
    for item in tag.find_all(subtype):
        if value in item.get(attribute, ''):
            return item


def parse_character_list(s, config):
    if ':' in s:
        s = s[s.index(':') + 1:]
    if s in config['char_translations']:
        s = config['char_translations'][s]

    c = [s]
    splitters = config.get('splitters', [' & ', '/', ' AND '])
    for splitter in splitters:
        x = []
        for s in c:
            x += s.split(splitter)
        c = x
    full_list = []
    for ss in c:
        ss = ss.strip()
        if len(ss) == 0:
            continue
        try:
            ss = str(ss)
        except:
            None
        if ss in config['char_translations']:
            full_list += parse_character_list(config['char_translations'][ss], config)
        else:
            full_list.append(ss)
    return full_list


def parse_characters(s, config, parse_stage_directions=True):
    D = {}
    for direction in ['spoken', 'sung', 'on phone']:
        key = ', ' + direction
        if key in s:
            s = s.replace(key, ' (%s)' % direction)
    s = s.upper()
    if s in config['char_translations']:
        s = config['char_translations'][s]
    m = PARENTHETICAL.match(s)
    if m and parse_stage_directions:
        D.update(parse_characters(m.group(1), config, parse_stage_directions))
        D['stage_direction'] = m.group(2)
        return D

    if 'EXCEPT' in s:
        s, _, except_s = s.partition('EXCEPT')
        D['except'] = parse_character_list(except_s, config)
    c = parse_character_list(s, config)
    if len(c) > 0:
        D['characters'] = c
    return D


def create_entry(header, lines, sections):
    for i, line in enumerate(lines):
        try:
            lines[i] = str(line)
        except:
            None
    entry = {'lines': lines}
    if header is None:
        header = {}
    if 'characters' not in header and len(sections) > 0:
        last_header = sections[-1].get('header', {})
        if 'characters' not in last_header and len(sections) > 1:
            last_header = sections[-2].get('header', {})
        if 'characters' in last_header:
            header['characters'] = list(last_header['characters'])
    if len(header) > 0:
        entry['header'] = header
    sections.append(entry)


def match_stage_direction(line):
    for pattern in STAGE_DIRECTION:
        m = pattern.match(line)
        if m:
            return m


def search_stage_direction(line):
    for pattern in STAGE_DIRECTION:
        m = pattern.search(line)
        if m:
            return m


def match_italic_chars(chars, tag):
    if len(chars) != 2:
        return None
    italic_pattern = re.compile('<' + tag.upper() + '>([^<]+)</' + tag.upper() + '>')
    m0 = italic_pattern.match(chars[0])
    m1 = italic_pattern.match(chars[1])
    if not m0 and m1:
        return [chars[0]], [m1.group(1)]
    return None


def match_paren_chars(chars):
    s = chars[-1]
    m = PARENTHETICAL.match(s)
    if m:
        groups = map(str.strip, m.groups())
        return chars[:-1] + [groups[0]], groups[1:]


def quick_section(chars, line_str):
    lines = [s for s in line_str.split('\n') if len(s.strip()) > 0]
    if len(lines) == 0:
        return None
    return {'header': {'characters': chars}, 'lines': lines}


def replace_pattern(section, char_translate_function, splitter_pattern):
    replacements = []
    chars = section.get('header', {}).get('characters', [])
    new_chars = char_translate_function(chars)
    if not new_chars:
        replacements.append(section)
        return replacements
    for c_set in new_chars:
        for i, char in enumerate(c_set):
            if char in config['char_translations']:
                c_set[i] = config['char_translations'][char]
    print new_chars

    full_lines = '\n'.join(section['lines'])
    while len(full_lines.strip()) > 0:
        m = splitter_pattern.search(full_lines)
        if m:
            a_section, b_section, full_lines = full_lines.partition(m.group(0))
            a = quick_section(new_chars[0], a_section)
            if a:
                replacements.append(a)
            b = quick_section(new_chars[1], m.group(1))
            if b:
                replacements.append(b)
        else:
            replacements.append(quick_section(new_chars[0], full_lines))
            break

    return replacements


def replace_italics(section, tag):
    italic_section = re.compile('<' + tag + '>([^<]+)</' + tag + '>')
    return replace_pattern(section, lambda x: match_italic_chars(x, tag), italic_section)


def replace_parentheticals(section):
    return replace_pattern(section, match_paren_chars, PAREN_SECTION)


def parse_simple_lyrics(s, config, global_char=None, parse_stage_directions=True):
    header = None
    sections = []
    lines = []

    for line in s.split('\n'):
        line = line.strip()
        if len(line) == 0:
            continue
        m0 = CHAR_LINE.match(line)
        m1 = match_stage_direction(line)

        if (m0 or m1) and len(lines) > 0:
            create_entry(header, lines, sections)
            lines = []

        if m0:
            header = {}

            char_s = m0.group(1)
            m = search_stage_direction(char_s)
            if m and parse_stage_directions:
                char_s = char_s.replace(m.group(0), '').strip()
                header['stage_direction'] = m.group(1)

            if config.get('require_caps_characters', False) and LOWERCASE.search(char_s):
                sd = header.get('stage_direction', '') + char_s
                sections.append({'stage_direction': sd})
                header = {}
            else:
                header.update(parse_characters(char_s, config, parse_stage_directions))
                if global_char:
                    header['characters'] = [global_char]
        elif parse_stage_directions and m1:
            sections.append({'stage_direction': m1.group(1)})
        else:
            lines.append(line)

    if global_char and header is None:
        header = {}
        header['characters'] = [global_char]
    if len(lines) > 0:
        create_entry(header, lines, sections)
    thus_far = set()
    both = None
    for section in all_sections(sections):
        chars = section.get('header', {}).get('characters', [])
        if chars == ['BOTH']:
            both = thus_far
            break
        thus_far.update(set(chars))

    if both and len(both) != 2:
        both = both - set(config.get('ignore_chars', []))
    if both and len(both) == 2:
        print 'BOTH = ', both
        for section in all_sections(sections):
            chars = section.get('header', {}).get('characters', [])
            if chars == ['BOTH']:
                section['header']['characters'] = list(both)
    for tag in ['i', 'b', 'em']:
        sections = section_map(sections, lambda x: replace_italics(x, tag))
    if not parse_stage_directions:
        sections = section_map(sections, replace_parentheticals)
    return sections

def parse_lyrics(s, config, global_char=None, parse_stage_directions=True):
    for a, b in config.get('global_translations', {}).iteritems():
        if a in s:
            s = s.replace(a, b)

    sections = []
    for bit in split_by_tables(s):
        if type(bit) == str:
            sections += parse_simple_lyrics(bit, config, global_char, parse_stage_directions)
        else:
            chunks = []
            for col in bit:
                chunks.append(parse_simple_lyrics(col, config, global_char, parse_stage_directions))
            sections.append({'simultaneous': chunks})

    return sections


def print_char_stats(stats):
    for name, count in sorted(stats.items(), key=lambda x: -x[1]):
        print '%5s %s' % (str(count), name)
    print len(stats)

if __name__ == '__main__':
    import argparse
    import os.path
    parser = argparse.ArgumentParser()
    parser.add_argument('config', nargs='+')
    parser.add_argument('--filter', nargs='?')
    parser.add_argument('-f', '--force', action='store_true')

    args = parser.parse_args()
    for config in args.config:
        slug = os.path.splitext(config)[0]
        config = yaml.load(open(config))

        # Rewrite Equivalent Chars
        if 'char_translations' not in config:
            config['char_translations'] = {}
        for key, row in config.get('equivalent_chars', {}).iteritems():
            if type(row) == str:
                config['char_translations'][row] = key
            else:
                for a in row:
                    config['char_translations'][a] = key

        for song in sorted(os.listdir(slug)):
            fn = os.path.join(slug, song)
            if args.filter and args.filter not in fn:
                continue
            song_config = yaml.load(open(fn))
            if 'raw_text' in song_config:
                song_config['lyrics'] = parse_lyrics(song_config['raw_text'], config,
                                                     song_config.get('global_char', []),
                                                     song_config.get('parse_stage_directions', True))
            yaml.dump(song_config, open(fn, 'w'))

        OVERALL = collections.defaultdict(int)
        for filename, song in sorted(get_songs(slug).items()):
            if args.filter and args.filter not in filename:
                continue
            print filename
            D = collections.defaultdict(int)
            for section in all_sections(song.get('lyrics', [])):
                if 'header' not in section or 'characters' not in section['header']:
                    continue
                for ch in section['header']['characters']:
                    if ch in config.get('ignore_chars', []):
                        continue
                    for line in section['lines']:
                        D[ch] += len(line.split())
                        OVERALL[ch] += len(line.split())

            print_char_stats(D)

        print
        print slug
        print_char_stats(OVERALL)
