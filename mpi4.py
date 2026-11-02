# ----- Mπ4 Media Player -----
# V1-rc1
# by Wikke Andeweg
# www.mpi4.org
# 2026

import os, glob, subprocess, threading, time, configparser, socket, json, warnings, re

from fnmatch import fnmatchcase
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from gpiozero import Button as GPIOButton
from gpiozero.mixins import CallbackSetToNone

warnings.filterwarnings('ignore', category=CallbackSetToNone)

# ---- HARDWARE DETECTION ----

#Get HDMI, Serial, Audio card and pi version
_hdmi = subprocess.run(['mpv', '--drm-connector=help'], capture_output=True, text=True).stdout
_serial = open('/proc/device-tree/serial-number').read().strip('\x00')
_model = int(open('/proc/device-tree/model').read().strip('\x00').split()[2])
_cards = {m[2]: int(m[1]) for m in re.finditer(r'^card (\d+): (\S+)', subprocess.run(['aplay', '-l'], capture_output=True, text=True).stdout, re.M)}

#Detect if HDMI is preset
USE_COMPOSITE = not re.search(r'HDMI.*\bconnected', _hdmi)

#Force Composite output if no HDMI is detected
if USE_COMPOSITE:
    force_path = subprocess.run(['sudo', 'find', '/sys/kernel/debug/dri', '-name', 'Composite-1'],capture_output=True, text=True).stdout.strip().split('\n')[0]
    if force_path:
        subprocess.run(f"echo on | sudo tee {force_path}/force", shell=True)

AUDIO_DEVICES = {
    'headphones': f'alsa/plughw:{_cards["Headphones"]},0' if "Headphones" in _cards else None,
    'hdmi0':      f'alsa/plughw:{_cards.get("vc4hdmi0", _cards.get("vc4hdmi"))},0',
    'hdmi1':      f'alsa/plughw:{_cards["vc4hdmi1"]},0' if "vc4hdmi1" in _cards else None,
}

DEFAULT_NAME = 'mpi4-' + _serial[-4:]

VIDEO_EXTS     = {'.mp4', '.mkv', '.avi', '.mov', '.m4v', '.webm', '.ts', '.mpeg','.wmv','.flv','.3gp'}
IMAGE_EXTS     = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
AUDIO_EXTS     = {'.mp3', '.wav','.flac','.ogg','.opus','.m4a','.aac'}
POLL_INTERVAL  = 5

STATUS_PORT = 5005     # UDP broadcast: status of every player
OSC_PORT    = 8000     # UDP: OSC control in
HTTP_PORT   = 8080     # TCP: web page + API
OBSERVED    = ['time-pos', 'duration', 'pause', 'path', 'idle-active', 'playlist-count']

NOMEDIA_IMAGE = '/home/pi/nomediapal.png' if USE_COMPOSITE else '/home/pi/nomedia.png'
DEFAULT_CONFIG_PATH = '/boot/firmware/default.mpi4' 
HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web.html')

# ---- GPIO ----

VALID_PINS = {4, 5, 6, 12, 13, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27}
BUTTONS = {pin: GPIOButton(pin, pull_up=True, bounce_time=0.05) for pin in VALID_PINS}

# ---- CONFIG ----

def load_config():
    config = configparser.ConfigParser()

    if os.path.isfile(DEFAULT_CONFIG_PATH):
        settings_files = [DEFAULT_CONFIG_PATH]
    else:
        settings_files = glob.glob('/media/*/settings.mpi4')

    if settings_files:
        config.read(settings_files[0])

    audio = config.get('player', 'audio_device', fallback='headphones')
    audio = 'hdmi0' if audio == 'hdmi' else audio
    image_duration = config.getint('player', 'image_duration', fallback=10)
    rotation = config.getint('player', 'rotation', fallback=0)
    force_rotation = config.getboolean('player', 'force_rotation', fallback=False)
    autoplay = config.getboolean('player', 'autoplay', fallback=True)

    follow      = config.getboolean('sync', 'role', fallback=False)
    sync_offset = config.getfloat('sync', 'offset', fallback=0.0)
    sync_id     = config.get('sync', 'id', fallback='0')
    name        = config.get('network', 'name', fallback=DEFAULT_NAME)

    buttons = dict(config.items('buttons')) if config.has_section('buttons') else {}

    return {
        'audio_device': AUDIO_DEVICES[audio],
        'image_duration': image_duration,
        'rotation':       rotation,
        'force_rotation': force_rotation,
        'follow':         follow,
        'sync_offset':    sync_offset,
        'sync_id':        sync_id,
        'name':           name,
        'autoplay':       autoplay,
        'buttons':        buttons,
    }

def build_args(cfg):
    args = [
        '--terminal=no',
        '--force-window=immediate',
        '--osc=no',
        '--audio-stream-silence=yes',
        f'--audio-device={cfg["audio_device"]}',
        '--input-ipc-server=/tmp/mpv.sock',
        f'--image-display-duration={cfg["image_duration"]}',
    ]

    if _model in (2, 3) and not cfg['force_rotation']:
        args.extend([
            '--vo=gpu',
            '--gpu-context=drm',
            '--hwdec=v4l2m2m',
            '--drm-draw-plane=overlay',
            '--drm-drmprime-video-plane=primary',
            '--profile=fast',
        ])
    else:
        args.append(f'--video-rotate={cfg["rotation"]}')

    return args
COMPOSITE_ARGS = [
    '--drm-connector=Composite-1',
    '--drm-mode=768x576',
    '--video-aspect-override=4:3',
]

# ---- MEDIA ----

def get_media():
    all_files = {os.path.realpath(f) for f in glob.glob('/media/*/*')}
    valid_exts = VIDEO_EXTS | IMAGE_EXTS | AUDIO_EXTS
    return sorted(f for f in all_files if os.path.splitext(f)[1].lower() in valid_exts)

def find_video(name):
    name = os.path.splitext(os.path.basename(name))[0].lower()
    matches = [f for f in get_media() if os.path.splitext(os.path.basename(f))[0].lower() == name]
    return matches[0] if matches else None

# ---- MPV CONTROLLER ----

def mpv_command(cmd):
    try:
        with socket.socket(socket.AF_UNIX) as s:
            s.connect('/tmp/mpv.sock')
            s.sendall((json.dumps({'command': cmd}) + '\n').encode())
            s.recv(4096)
    except OSError:                                  
        pass

def observer():  # Read data from mpv
    s = socket.socket(socket.AF_UNIX)
    for _ in range(50):
        try:
            s.connect('/tmp/mpv.sock')
            break
        except OSError:
            time.sleep(0.1)
    else:
        return
    for i, prop in enumerate(OBSERVED, 1):
        s.sendall((json.dumps({'command': ['observe_property', i, prop]}) + '\n').encode())
    for line in s.makefile('rb'):
        msg = json.loads(line)
        if msg.get('event') != 'property-change':
            continue
        now, name, data = time.monotonic(), msg['name'], msg.get('data')
        PROPS[name] = data
        if name == 'time-pos':
            PROPS['_t'] = now
        elif name == 'path':             
            PROPS['_t0'] = now
            PROPS['_pause_at'] = now if PROPS.get('pause') else None
        elif name == 'pause':
            if data:
                PROPS['_pause_at'] = now
            elif PROPS.get('_pause_at'):
                PROPS['_t0'] += now - PROPS['_pause_at']
                PROPS['_pause_at'] = None
    s.close()

# ---- SHARED STATE ----

CFG = {}
CURRENT_MEDIA = []    
PROPS = {}            
FOLLOWING = ''        

def playerstate():
    path = PROPS.get('path')
    ext  = os.path.splitext(path or '')[1].lower()

    if not CURRENT_MEDIA:
        state = 'N'                                  # no media
    elif not path or PROPS.get('idle-active'):
        state = 'B'                                  # black / idle
    elif PROPS.get('pause'):
        state = 'H'                                  # paused
    else:
        state = 'P'                                  # playing

    kind = '-'
    if state in ('P', 'H'):
        kind = 'V' if ext in VIDEO_EXTS else 'A' if ext in AUDIO_EXTS else 'S'

    if kind == 'S':
        dur = CFG['image_duration']
        now = time.monotonic()
        pos = min((PROPS.get('_pause_at') or now) - PROPS.get('_t0', now), dur)
    elif kind in ('V', 'A'):
        dur = PROPS.get('duration') or 0
        tp = PROPS.get('time-pos')
        pos = 0 if tp is None else tp if PROPS.get('pause') else tp + min(time.monotonic() - PROPS.get('_t', 0), 0.25)   
    else:
        dur = pos = 0

    return {
        'name': CFG['name'], 'sync_id': CFG['sync_id'], 'state': state, 'kind': kind,
        'index': CURRENT_MEDIA.index(path) + 1 if path in CURRENT_MEDIA else 0,
        'count': len(CURRENT_MEDIA), 'pos': pos, 'dur': dur, 'left': max(dur - pos, 0),
        'role': 'F' if CFG['follow'] else 'P',
        'file': os.path.basename(path) if kind != '-' else '',
        'source': FOLLOWING,
    }

def goto(n):
    if 1 <= n <= len(CURRENT_MEDIA):
        if PROPS.get('playlist-count') == len(CURRENT_MEDIA):
            mpv_command(['playlist-play-index', n - 1])
        else:
            mpv_command(['loadfile', CURRENT_MEDIA[n - 1], 'replace'])

# ---- COMMANDS ----

def dispatch(action, arg=None):
    if CFG['follow']:
        return False
    if action == 'play':
        mpv_command(['set_property', 'pause', False])
    elif action == 'pause':
        mpv_command(['set_property', 'pause', True])
    elif action == 'toggle':
        mpv_command(['cycle', 'pause'])
    elif action == 'next':
        mpv_command(['playlist-next'])
    elif action == 'previous':
        mpv_command(['playlist-prev'])
    elif action == 'goto':
        goto(int(arg))
    elif action == 'seek':
        mpv_command(['seek', float(arg), 'absolute'])
    else:
        path = find_video(arg if action == 'video' else action)
        if not path:
            return False
        mpv_command(['loadfile', path, 'replace'])
    return True

# ---- BUTTONS ----

def assign_buttons(cfg):
    for btn in BUTTONS.values():
        btn.when_pressed = None
    for pin, action in cfg['buttons'].items():
        BUTTONS[int(pin)].when_pressed = lambda a=action: dispatch(a)

# ---- STATUS PROTOCOL ----
#   MPI4|1|name|syncid|state|kind|index|count|pos|dur|role|file
#   MPI4: Always a static name
#   1: protocol version number. can be checked if future updates break compatibility 
#   syncid: For multiple sync groups
#   state: P playing  H paused  B black/idle  N no media
#   kind:  V video  A audio  S still  - none
#   count: number of files in playlist
#   pos/dur in seconds
#   role:  P Player F follower
#   File is the rest of the packet (may contain |)

def encode_status(s):
    return '|'.join(['MPI4', '1', s['name'], s['sync_id'], s['state'], s['kind'],
                     str(s['index']), str(s['count']), '%.2f' % s['pos'], '%.1f' % s['dur'],
                     s['role'], s['file'][:40]]).encode()

def decode_status(data):
    f = data.decode('utf-8', 'ignore').split('|', 11)
    if len(f) != 12 or f[0] != 'MPI4' or f[1] != '1':
        return None
    return {'name': f[2], 'sync_id': f[3], 'state': f[4], 'kind': f[5], 'index': int(f[6]),
            'count': int(f[7]), 'pos': float(f[8]), 'dur': float(f[9]), 'role': f[10], 'file': f[11]}

def broadcaster():
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    targets, refreshed, last_key, last_sent = [], 0, None, 0
    while True:
        now = time.monotonic()
        if now - refreshed > 2:    
            out = subprocess.run(['ip', '-4', '-o', 'addr', 'show'], capture_output=True, text=True).stdout
            targets, refreshed = re.findall(r'brd (\S+)', out), now
        s = playerstate()
        key = (s['state'], s['kind'], s['index'], s['file'], s['role'])
        if s['state'] == 'P' or key != last_key or now - last_sent >= 1:  
            packet = encode_status(s)
            for target in targets:
                try:
                    udp.sendto(packet, (target, STATUS_PORT))
                except OSError:
                    pass
            last_key, last_sent = key, now
        time.sleep(0.1)

# ---- FOLLOWER ----

SYNC = {'last_goto': 0.0, 'nudged': False}

def sync_to(p):
    me = playerstate()
    want_pause = p['state'] == 'H'
    if want_pause != bool(PROPS.get('pause')):
        mpv_command(['set_property', 'pause', want_pause])

    if p['count'] == me['count'] and p['index'] and p['index'] != me['index']:
        if time.monotonic() - SYNC['last_goto'] > 1.5:          
            goto(p['index'])
            SYNC['last_goto'] = time.monotonic()
        return

    if p['kind'] == 'S' or me['kind'] not in ('V', 'A') or p['dur'] <= 0 or PROPS.get('time-pos') is None:
        return
    current = me['pos']
    if current is None:
        return
    dur  = p['dur']
    diff = (p['pos'] - CFG['sync_offset'] - current + dur / 2) % dur - dur / 2   
    if abs(diff) > 0.5:
        mpv_command(['seek', (current + diff) % dur, 'absolute'])
    elif abs(diff) > 0.05:
        mpv_command(['set_property', 'speed', max(0.9, min(1.1, 1.0 + diff * 0.5))])
        SYNC['nudged'] = True
    elif SYNC['nudged']:
        mpv_command(['set_property', 'speed', 1.0])
        SYNC['nudged'] = False

def follower():
    global FOLLOWING
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)    
    udp.settimeout(1.0)
    udp.bind(('', STATUS_PORT))
    sources = {}
    while True:
        try:
            data, _ = udp.recvfrom(512)
        except socket.timeout:
            data = None
        if not CFG['follow']:
            FOLLOWING = ''
            continue
        now = time.monotonic()
        p = decode_status(data) if data else None
        if p and p['role'] == 'P' and p['sync_id'] == CFG['sync_id']:
            sources[p['name']] = (now, p)
        live = [n for n, (t, _) in sources.items() if now - t < 2]
        FOLLOWING = min(live) if live else ''
        if p and p['name'] == FOLLOWING and p['state'] in ('P', 'H'):
            sync_to(p)

# ---- WEB PAGE + API ----

class Web(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, body, ctype='application/json', code=200):
        data = body.encode()
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/':
            self.reply(open(HTML_PATH).read(), 'text/html; charset=utf-8')
        elif path == '/api/status':
            self.reply(json.dumps(playerstate()))
        elif path == '/api/playlist':
            self.reply(json.dumps([os.path.basename(f) for f in CURRENT_MEDIA]))
        else:
            self.reply('{}', code=404)

    def do_POST(self):
        url = urlparse(self.path)
        if not url.path.startswith('/api/'):
            return self.reply('{}', code=404)
        ok = dispatch(url.path[5:], parse_qs(url.query).get('arg', [None])[0])
        self.reply(json.dumps({'ok': ok}), code=200 if ok else 409)

def web_server():
    ThreadingHTTPServer(('0.0.0.0', HTTP_PORT), Web).serve_forever()

# ---- OSC IN ----
# /mpi4/<action> [arg]            -> whoever receives it
# /mpi4/<name>/<action> [arg]     -> only players whose name matches (wildcards allowed: /mpi4/wall-*/pause)

def osc_handler(address, *args):
    parts = address.strip('/').split('/')
    if parts[0] != 'mpi4' or len(parts) not in (2, 3):
        return
    if len(parts) == 3 and not fnmatchcase(CFG['name'], parts[1]):
        return
    dispatch(parts[-1], args[0] if args else None)

def osc_server():
    osc = Dispatcher()
    osc.set_default_handler(osc_handler)
    ThreadingOSCUDPServer(('0.0.0.0', OSC_PORT), osc).serve_forever()

# ---- WATCHER ----

def watcher(player, current_media):
    while player.poll() is None:
        time.sleep(POLL_INTERVAL)
        if get_media() != current_media:
            player.terminate()

# ---- SERVICES ----

def keep_alive(service):
    while True:
        try:
            service()
        except Exception as e:
            print(f'{service.__name__} stopped ({e!r}), restarting')
            time.sleep(1)

CFG = load_config()
for service in (broadcaster, follower, web_server, osc_server):
    threading.Thread(target=keep_alive, args=(service,), daemon=True).start()

# ---- MAIN LOOP ----

while True:
    CFG = load_config()
    assign_buttons(CFG)
    media = CURRENT_MEDIA = get_media()
    PROPS.clear()
    args  = build_args(CFG)
    if USE_COMPOSITE:
        args += COMPOSITE_ARGS

    if not media:
        player = subprocess.Popen(['mpv'] + args + ['--loop-playlist=inf'] + [NOMEDIA_IMAGE])

    elif CFG['autoplay']:
        player = subprocess.Popen(['mpv'] + args + ['--loop-playlist=inf'] + media)

    else:
        player = subprocess.Popen(['mpv'] + args + ['--idle=yes', '--keep-open=no'])

    threading.Thread(target=observer, daemon=True).start()
    threading.Thread(target=watcher, args=(player, media), daemon=True).start()

    player.wait()
