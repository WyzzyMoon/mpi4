# ----- Mπ4 Media Player -----
# V1.0b3
# by Wikke Andeweg
# www.mpi4.org
# 2026

import os, glob, subprocess, threading, time, configparser, socket, json, warnings, re
from gpiozero import Button as GPIOButton
from gpiozero.mixins import CallbackSetToNone
warnings.filterwarnings('ignore', category=CallbackSetToNone)

# ---- HARDWARE DETECTION ----

_hdmi = subprocess.run(['mpv', '--drm-connector=help'], capture_output=True, text=True).stdout
USE_COMPOSITE = 'HDMI-A-1 (connected)' not in _hdmi and 'HDMI-A-2 (connected)' not in _hdmi
if USE_COMPOSITE:
    force_path = subprocess.run(['sudo', 'find', '/sys/kernel/debug/dri', '-name', 'Composite-1'],
                                 capture_output=True, text=True).stdout.strip().split('\n')[0]
    if force_path:
        subprocess.run(f"echo on | sudo tee {force_path}/force", shell=True)

CARDS = [line.split(':')[1].strip().split()[0] for line in subprocess.run("aplay -l | grep '^card'", shell=True, capture_output=True, text=True).stdout.splitlines()]

AUDIO_DEVICES = {
    'headphones': f'alsa/plughw:{CARDS.index("Headphones")},0' if "Headphones" in CARDS else None,
    'hdmi0':      f'alsa/plughw:{next((i for i,c in enumerate(CARDS) if "vc4hdmi0" in c or ("vc4hdmi" in c and "vc4hdmi1" not in c)), None)},0',
    'hdmi1':      f'alsa/plughw:{next((i for i,c in enumerate(CARDS) if "vc4hdmi1" in c), None)},0',
}

VIDEO_EXTS     = {'.mp4', '.mkv', '.avi', '.mov', '.m4v', '.webm'}
IMAGE_EXTS     = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
AUDIO_EXTS     = {'.mp3', '.wav'}
DEFAULT_IMAGE_DURATION = 10 
POLL_INTERVAL  = 5

NOMEDIA_IMAGE = '/home/pi/nomediapal.png' if USE_COMPOSITE else '/home/pi/nomedia.png'
DEFAULT_CONFIG_PATH = '/boot/firmware/default.mpi4' 

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
    image_duration = config.getint('player', 'image_duration', fallback=DEFAULT_IMAGE_DURATION)
    rotation = config.getint('player', 'rotation', fallback=0)
    autoplay = config.getboolean('player', 'autoplay', fallback=True)

    role        = config.get('sync', 'role', fallback='standalone')
    sync_offset = config.getfloat('sync', 'offset', fallback=0.0)
    sync_id     = config.get('sync', 'id', fallback='default')

    buttons = dict(config.items('buttons')) if config.has_section('buttons') else {}

    wall_enabled = config.getboolean('videowall', 'enabled', fallback=False)
    wall_cols = config.getint('videowall', 'cols', fallback=2)
    wall_rows = config.getint('videowall', 'rows', fallback=2)
    try:
        wall_row, wall_col = (int(x) for x in config.get('videowall', 'position', fallback='0,0').split(','))
    except ValueError:
        wall_row, wall_col = 0, 0

    return {
        'audio_device':   AUDIO_DEVICES.get(audio, AUDIO_DEVICES['headphones']),
        'image_duration': image_duration,
        'rotation':       rotation,
        'role':           role,
        'sync_offset':    sync_offset,
        'sync_id':        sync_id,
        'autoplay':       autoplay,
        'buttons':        buttons,
        'wall_enabled':   wall_enabled,
        'wall_cols':      wall_cols,
        'wall_rows':      wall_rows,
        'wall_row':       wall_row,
        'wall_col':       wall_col,
    }

def build_vf(cfg):
    filters = []
    if cfg['rotation'] == 90:
        filters.append('transpose=1')
    elif cfg['rotation'] == 180:
        filters += ['hflip', 'vflip']
    elif cfg['rotation'] == 270:
        filters.append('transpose=2')

    if cfg['wall_enabled']:
        cols, rows = cfg['wall_cols'], cfg['wall_rows']
        col, row   = cfg['wall_col'], cfg['wall_row']
        filters.append(f'crop=iw/{cols}:ih/{rows}:(iw/{cols})*{col}:(ih/{rows})*{row}')

    return filters

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
    vf = build_vf(cfg)
    if vf:
        args.append('--vf=lavfi=[' + ','.join(vf) + ']')
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
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect('/tmp/mpv.sock')
        s.sendall((json.dumps({'command': cmd}) + '\n').encode())
        response = json.loads(s.recv(4096))
        s.close()
        return response.get('data')
    except:
        return None

# ---- BUTTONS ----

def assign_buttons(cfg):
    for btn in BUTTONS.values():
        btn.when_pressed = None
    for pin, action in cfg['buttons'].items():
        if int(pin) in BUTTONS:
            btn = BUTTONS[int(pin)]
            btn.when_pressed = lambda a=action: handle_button(a)

def handle_button(action):
    if action in ('play', 'pause'):
        mpv_command(['cycle', 'pause'])
    elif action == 'next':
        mpv_command(['playlist-next'])
    elif action == 'previous':
        mpv_command(['playlist-prev'])
    else:
        path = find_video(action)
        if path:
            mpv_command(['loadfile', path, 'replace'])

# ---- SYNC ----

def leader(player, sync_id):
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    targets, refreshed = [], 0
    while player.poll() is None:
        if time.time() - refreshed > 2:
            out = subprocess.run(['ip', '-4', '-o', 'addr', 'show'], capture_output=True, text=True).stdout
            targets, refreshed = re.findall(r'brd (\S+)', out), time.time()
        position = mpv_command(['get_property', 'playback-time'])
        if position is not None:
            packet = json.dumps({'id': sync_id, 'position': position}).encode()
            for target in targets:
                try:
                    udp.sendto(packet, (target, 5005))
                except OSError:
                    pass
        time.sleep(0.1)
    udp.close()

def follower(player, sync_id, offset):
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp.settimeout(1.0)
    udp.bind(('', 5005))
    nudged = False
    while player.poll() is None:
        try:
            data, _ = udp.recvfrom(1024)
            packet = json.loads(data)
            if packet.get('id') != sync_id:
                continue
            target = packet['position'] - offset
            current = mpv_command(['get_property', 'playback-time'])
            if current is None:
                continue
            diff = target - current
            if abs(diff) > 0.5:
                mpv_command(['seek', target, 'absolute'])
            elif abs(diff) > 0.05:
                mpv_command(['set_property', 'speed', max(0.9, min(1.1, 1.0 + diff * 0.5))])
                nudged = True
            elif nudged:
                mpv_command(['set_property', 'speed', 1.0])
                nudged = False
        except socket.timeout:
            continue
    udp.close()

# ---- WATCHER ----

def watcher(player, current_media):
    while player.poll() is None:
        time.sleep(POLL_INTERVAL)
        if get_media() != current_media:
            player.terminate()

# ---- MAIN LOOP ----

while True:
    cfg = load_config()
    assign_buttons(cfg)
    media = get_media()
    args  = build_args(cfg)
    if USE_COMPOSITE:
        args += COMPOSITE_ARGS

    if not media:
        player = subprocess.Popen(['mpv'] + args + ['--loop-playlist=inf'] + [NOMEDIA_IMAGE])

    elif cfg['autoplay']:
        player = subprocess.Popen(['mpv'] + args + ['--loop-playlist=inf'] + media)

    else:
        player = subprocess.Popen(['mpv'] + args + ['--idle=yes', '--keep-open=no'])

    threading.Thread(target=watcher, args=(player, media), daemon=True).start()

    if cfg['role'] == 'leader':
        threading.Thread(target=leader, args=(player, cfg['sync_id']), daemon=True).start()

    elif cfg['role'] == 'follower':
        threading.Thread(target=follower, args=(player, cfg['sync_id'], cfg['sync_offset']), daemon=True).start()

    player.wait()
