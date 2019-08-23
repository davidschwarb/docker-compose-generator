
#   
#  Developed by David Schwarb 8/22/2019
#  Intended for use converting CLI docker service create comands to the easier to scale docker compose structure
#  

def dockerComposeGenerator(cmd):
    '''Takes docker service create command and generates an equivelent docker compose file
   Surround your multi word constraints with single quotes.
   Command structure is "docker service create [OPTIONS] IMAGE [COMMAND]"'''
    
    def cleanCommand(cmd):
        '''Function cleans the docker service command, and returns a list to cmd'''
        cmd = cmd.strip('\n ')
        cmd = cmd.split('\n')
        for i in range(len(cmd)):
            cmd[i] = cmd[i].strip()
            cmd[i] = cmd[i].lstrip('docker service create')

        #Parse the command into its sub sections
        for i in range(len(cmd)):
            cmd[i] = cmd[i].split()
        return cmd
    
    
    def parseCommands(cmd):
        '''Takes a list of commands and returns a dictionary of command:value returns'''
         #Search for '-' specifying command switches
        oneWordIndexes = []                            #Holds the indexes of commands with one word
        oneWordOptions = ['d', 'detach', 'no-healthcheck', 'no-resolve-image', 'q', 'quiet', 'read-only']
        multiWordIndexes = []
        tempIndex = []
        commands = {}
        for i in range(len(cmd)):                      #Searches for '-' and '=' declaring commands
            if cmd[i].lstrip('-') in oneWordOptions:   #searches for one word options and, if found, updates them to commands
                commands.update({cmd[i].lstrip('-'): cmd[i].lstrip('-')})
                cmd[i] = ' '

            if "'" in cmd[i] or '"' in cmd[i]:  #Searches for quotes in the index, representing a multi word (String) command
                if (cmd[i][0] == "'" and cmd[i][-1] == "'") or (cmd[i][0] == '"' and cmd[i][-1] == '"'):
                    commands.update({cmd[i-1]: cmd[i]})
                    continue
                tempIndex.append(i)
                if len(tempIndex) == 2:            #If there is a pair of indexes, it pushes the temp value to the main list
                    multiWordIndexes.append(tempIndex)
                    tempIndex = []                 #Sets temp list back to empty
                continue
            if cmd[i][0] == '-':                       #if the first character is a dash, then it is an option in the command
                cmd[i] = cmd[i].lstrip('-')
                if '=' in cmd[i]:                      #if there is an '=' in the command it will be added to oneWordIndexes
                    oneWordIndexes.append(i)
                    continue
                elif "'" in cmd[i+1] or '"' in cmd[i+1]:        #if there is a qote in the next command, continue the loop
                    continue
                if commands.get(cmd[i]):               #if the command already exists, push it as a list
                    if not isinstance(commands.get(cmd[i]), list):
                        cmdHolder = [commands.get(cmd[i])]
                    cmdHolder.append(cmd[i+1])
                    commands.update({cmd[i]: cmdHolder})
                else:                               #if neither of the previous if's are true; push key pair to commands dict
                    commands.update({cmd[i]: cmd[i+1]})
#             else:
#                 print(cmd[i])
        #Joins the multi word CMD strings
        for start,end in multiWordIndexes:             #start and end represent where the multi word command begins and ends
                commands.update({cmd[start-1]:' '.join(cmd[start:end+1])})

        #Appends the single word CMD string
        for i in oneWordIndexes:
            key, value = cmd[i].split('=')      #splits the single word cmd string by the equal sign and returns key, value
            commands.update({key:value})

        #processes volume mounts
        volumes = {}
        if commands.get('mount'):                   #if there are volume mounts, create a subdictionary to hold mount pairs
            mount = commands.get('mount').split(',')
            for mountCommands in mount:
                k,v = mountCommands.split('=',1)
                volumes.update({k: v})
            commands.update({'mount': volumes})

        #Get the command, and optionally any args
        
        if cmd:
            if ':' in cmd[-1]:
                commands.update({'image': cmd[-1]})
            elif ':' in cmd[-2]:
                commands.update({'image': cmd[-2]})
                commands.update({'arg': cmd[-1]})
        return commands
    
    def formatOutput(commands, networks):
        '''Takes a dicitionary of name:command pairs and returns a formatted version of them'''
            #Generate yml format for the command.
        #Basic output template
        output = ('\n    {}:' +
                  '\n        image: {}').format(commands.get('name'),commands.get('image'))
        if commands.get('arg'):
            output += ('\n        command: {}').format(commands.get('arg'))

        #IF replicas or constraint are in the commands, there is a neccassary prereq tier "deploy"
        if commands.get('replicas') or commands.get('constraint'):
            output += ('\n        deploy:')
            if commands.get('replicas'):
                output += ('\n            replicas: {}').format(commands.get('replicas'))
            if commands.get('constraint'):
                output += ('\n            placement:' + 
                           '\n                constraints: {}').format('[' + commands.get('constraint').strip('\'\"') + ']')

        #if there are mount commands, the volumes tier is required
        if commands.get('mount'):
            output += ('\n        volumes:')
            mountCommands = commands.get('mount')
            if mountCommands.get('type'):
                output += '\n            - type: {}'.format(mountCommands.get('type'))
                if mountCommands.get('source'):
                    output += '\n              source: {}'.format(mountCommands.get('source'))
                if mountCommands.get('destination'):
                    output += '\n              target: {}'.format(mountCommands.get('destination'))
            else:
                print('Error: mount \'type\' is required')

        if commands.get('publish'):
            output += ('\n        ports:')
            if isinstance(commands.get('publish'), list):
                for port in commands.get('publish'):
                    output += ('\n            - "{}"').format(port)
            else:
                output += ('\n            - "{}"').format(commands.get('publish'))
        elif commands.get('p'):
            output += ('\n        ports:') 
            if isinstance(commands.get('p'), list):
                for port in commands.get('p'):
                    output += ('\n            - "{}"').format(port)
            else: 
                output += ('\n            - "{}"').format(commands.get('p'))

        if commands.get('network') or commands.get('hostname'):
            output += ('\n        networks:')

            if commands.get('hostname'):
                output += ('\n            {}:' +
                           '\n                 aliases:' +
                           '\n                     - {}').format(commands.get('network'),commands.get('hostname'))
            else:
                output += ('\n            - {}').format(commands.get('network'))        

        #append network information to the end
        if commands.get('network'):
            if commands.get('network') not in networks:
                networks.append(commands.get('network'))
        return output
    
    def formatMultipleServices(commands, networks):
        '''Intermediate step to process multiple services requires networks to be passed in, updated by reference'''
        output = ('version: "3"' + 
                  '\nservices:')
        for service in commands:
            output += formatOutput(service, networks)
        if networks:
            output += ('\nnetworks:')
            for network in networks:
                output += ('\n    {}:').format(network)
        return output
    
    #Lists the commands which are not transferrable from docker service to docker compose
    notPortableList = ['q', 'quiet', 'no-resolve-image'] 
    
    def badImplementation(commands):
        warned = False
        #Prints warnings for overlooked commands
        for dictionary in commands:
            for key in dictionary.keys():
                if type(dictionary.get(key)) is dict:
                    for innerKey in dictionary.get(key):
                        if dictionary.get(key).get(innerKey).strip('\'"') not in output \
                        and dictionary.get(key).get(innerKey).strip('\'"') not in notPortableList:
                            if not warned:
                                print('WARNING: The following options may not have been implemented...')
                                warned = True
                            print(innerKey + '=' + dictionary.get(key).get(innerKey))
                elif type(dictionary.get(key)) is list:
                    for option in dictionary.get(key):
                        if option.strip('\'"') not in output \
                        and option.strip('\'"') not in notPortableList:
                            if not warned:
                                print('WARNING: The following options may not have been implemented...')
                                warned = True
                            print('--' + key, option)
                elif dictionary.get(key).strip('\'"') not in output \
                and dictionary.get(key).strip('\'"') not in notPortableList:
                    if not warned:
                        print('WARNING: The following options may not have been implemented...')
                        warned = True
                    print('--' + key, dictionary.get(key))
        print()
        
    def notPortable(commands): 
        printed = False
        for i in range(len(commands)):
            for key in commands[i].keys():
                if key in notPortableList:
                    if not printed:
                        print('WARNING:\n '+
                              'The following options are not transferable from docker service commands'+
                              ' to docker compose structure:')
                        printed = True
                    print('--' + key)
        print()
        
    if cmd.isspace() or cmd == '':
        print('Please enter a docker service command string as a function argument\n' +
              'Command structure is "docker service create [OPTIONS] IMAGE [COMMAND]\"')
        return 1
    
    #Cleans the command of extra words
    cmd = cleanCommand(cmd)

    commands = []
    #Parses the commands and creates a dictionary of name:command pairs
    for command in cmd:
        commands.append(parseCommands(command))
        
    #Parses the name:command dictionary into yml formatting for the file
    networks = []
    output = formatMultipleServices(commands, networks)

    #Prints an error
    if 'None' in output:
        print('ERROR: Missing an argument. SEE \'None\' below')
    
    #Prints warnings for overlooked commands
    badImplementation(commands)
    
    #Checks commands against a list of known not portable commands, prints warnings if they match
    notPortable(commands)
    
    print(output)
#     print(cmd, end='\n\n')
#     print(commands)
    return(output)