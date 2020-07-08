#!/usr/bin/python

import argparse, os, subprocess, time, math, sys, errno

MVSDirectory = ''
outputDirectory = ''

def createParser():
    parser = argparse.ArgumentParser(description='OpenMVG/OpenMVS pipeline')
    parser._action_groups.pop()

    required = parser.add_argument_group('Required arguments')
    required.add_argument('--input',
        help='Input images folder',
        required=True)
    required.add_argument('--output', 
        help='Output path',
        required=True)

    imageListing = parser.add_argument_group('OpenMVG Image Listing')
    imageListing.add_argument('--flength',
        type=float,
        help='If your camera is not listed in the camera sensor database, you can set pixel focal length here. The value can be calculated by max(width-pixels, height-pixels) * focal length(mm) / Sensor width')

    computeFeature = parser.add_argument_group('OpenMVG Compute Features')
    computeFeature.add_argument('--dpreset',
        help='Used to control the Image_describer configuration. Default: NORMAL',
        choices=['NORMAL', 'HIGH', 'ULTRA'])

    computeMatches = parser.add_argument_group('OpenMVG Compute Matches')
    computeMatches.add_argument('--geomodel',
        help='Compute Matches geometric model: f: Fundamental matrix filtering (default) For Incremental SfM e: Essential matrix filtering For Global SfM h: Homography matrix filtering For datasets that have same point of projection',
        choices=['f', 'e', 'h'])

    return parser
    
def createCommands(args):
    imageListingOptions = []
    computeFeaturesOptions = []
    computeMatchesOptions = []
    reconstructMeshOptions = []
    refineMeshOptions = []
    textureMeshOptions = []
    commands = []

    inputDirectory = args.input
    global outputDirectory
    outputDirectory = args.output
    matchesDirectory = os.path.join(outputDirectory, 'matches')
    reconstructionDirectory = os.path.join(outputDirectory, 'reconstruction_global')
    global MVSDirectory
    MVSDirectory = os.path.join(outputDirectory, 'omvs')
    openmvgBin = '/opt/openmvg/bin'
    cameraSensorsDB = '/opt/openmvg/share/openMVG/sensor_width_camera_database.txt'
    openmvsBin = '/opt/openmvs/bin/OpenMVS'

    computeFeaturesOptions += ['-f', '1']
    computeMatchesOptions += ['-f', '1']

    # OpenMVG Image Listing]
    imageListingOptions += ['-c', 2]
    if args.flength != None:
        imageListingOptions += ['-f', args.flength]

    # OpenMVG Compute Features
    if args.dpreset != None:
        computeFeaturesOptions += ['-p', args.dpreset.upper()]

    # OpenMVG Match Matches
    if args.geomodel != None:
        computeMatchesOptions += ['-g', args.geomodel]

    # Create commands

    commands.append({
       'title': 'Instrics analysis',
       'command': [os.path.join(openmvgBin, 'openMVG_main_SfMInit_ImageListing'),  '-i', inputDirectory, '-o', matchesDirectory, '-d', cameraSensorsDB] + imageListingOptions
    })

    commands.append({
        'title': 'Compute features',
        'command': [os.path.join(openmvgBin, 'openMVG_main_ComputeFeatures'),  '-i', os.path.join(matchesDirectory, 'sfm_data.json'), '-o', matchesDirectory, '-m', 'SIFT'] + computeFeaturesOptions
    })

    commands.append({
        'title': 'Compute matches',
        'command': [os.path.join(openmvgBin, 'openMVG_main_ComputeMatches'),  '-i', os.path.join(matchesDirectory, 'sfm_data.json'), '-o', matchesDirectory] + computeMatchesOptions
    })

    commands.append({
        'title': 'Do Global reconstruction',
        'command': [os.path.join(openmvgBin, 'openMVG_main_GlobalSfM'), '-i',
                    os.path.join(matchesDirectory, 'sfm_data.json'), '-m', matchesDirectory, '-o',
                    reconstructionDirectory]
    })

    sceneFileName = ['scene']

    commands.append({
        'title': 'Convert OpenMVG project to OpenMVS',
        'command': [os.path.join(openmvgBin, 'openMVG_main_openMVG2openMVS'), '-i',
                    os.path.join(reconstructionDirectory, 'sfm_data.bin'), '-o',
                    os.path.join(MVSDirectory, 'scene.mvs'), '-d', MVSDirectory]
    })

    commands.append({
        'title': 'Densify point cloud',
        'command': [os.path.join(openmvsBin, 'DensifyPointCloud'), 'scene.mvs', '-v', '0']
    })

    sceneFileName.append('dense')

    mvsFileName = '_'.join(sceneFileName) + '.mvs'
    commands.append({
        'title': 'Reconstruct mesh',
        'command': [os.path.join(openmvsBin, 'ReconstructMesh'), mvsFileName, '-v', '0'] + reconstructMeshOptions
    })
    sceneFileName.append('mesh')

    mvsFileName = '_'.join(sceneFileName) + '.mvs'

    commands.append({
        'title': 'Refine mesh',
        'command': [os.path.join(openmvsBin, 'RefineMesh'), mvsFileName, '-v', '0'] + refineMeshOptions
    })
    sceneFileName.append('refine')

    mvsFileName = '_'.join(sceneFileName) + '.mvs'
    commands.append({
        'title': 'Texture mesh',
        'command': [os.path.join(openmvsBin, 'TextureMesh'), mvsFileName, '-v', '0'] + textureMeshOptions
    })

    commands.append({
        'title': 'remove matches',
        'command': ['rm', '-rf', matchesDirectory]
    })

    commands.append({
        'title': 'remove reconstruction',
        'command': ['rm', '-rf', reconstructionDirectory]
    })

    commands.append({
        'title': 'change directory',
        'command': ['cd', MVSDirectory]
    })

    commands.append({
        'title': 'cleanup mvs',
        'command': ['rm', '-rf',
                    '*.logs',
                    '*.dmap',
                    'scene.mvs',
                    'scene_dense.mvs',
                    'scene_dense.ply',
                    'scene_dense_mesh.mvs',
                    'scene_dense_mesh.ply',
                    'scene_dense_mesh_refine.mvs',
                    'scene_dense_mesh_refine.ply',
                    'scene_dense_mesh_refine_texture.mvs']
    })

    return commands

def runCommand(cmd):
    cwd = outputDirectory
    if "OpenMVS" in cmd[0]:
        cwd = MVSDirectory
    try:
        p = subprocess.Popen(cmd, cwd = cwd)
        p.communicate()
        return p.returncode
    except OSError as err:
        if err.errno == errno.ENOENT:
            print("Could not find executable: {0} - Have you installed all the requirements?".format(cmd[0]))
        else:
            print("Could not run command: {0}".format(err))
        return -1
    except:
        print("Could not run command")
        return -1

def runCommands(commands):
    startTime = int(time.time())
    for instruction in commands:
        print(instruction['title'])
        print('=========================================================================')
        print(' '.join(map(str, instruction['command'])))
        print('')
        rc = runCommand(map(str, instruction['command']))
        if rc != 0:
            print('Failed while executing: ' )
            print(' '.join(map(str, instruction['command'])))
            sys.exit(1)
    endTime = int(time.time())

    timeDifference = endTime - startTime
    hours = int(math.floor(timeDifference / 60 / 60))
    minutes = int(math.floor((timeDifference - hours * 60 * 60) / 60))
    seconds = int(math.floor(timeDifference - (hours * 60 * 60 + minutes * 60)))
    print('\n\nFinished without errors (I guess) - Used time: {0}:{1}:{2}'.format(
        ('00' + str(hours))[-2:], 
        ('00' + str(minutes))[-2:], 
        ('00' + str(seconds))[-2:]))

parser = createParser()
args = parser.parse_args()
commands = createCommands(args)
runCommands(commands)
