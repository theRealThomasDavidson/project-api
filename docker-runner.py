import os
import shutil
from subprocess import run
from dotenv import dotenv_values
from sys import argv, exit

def substitute_variables(template_path, output_path, testing):
    # Read the template SQL file
    with open(template_path, 'r') as template_file:
        template = template_file.read()

    # Load environment variables from .env

    dotenv_path = os.path.join(os.path.dirname(__file__), '.env'+(".testing"*testing ))

    # Create the substitution dictionary from dotenv variables
    substitution_dict = dict(dotenv_values(dotenv_path))

    # Perform variable substitution
    for key, value in substitution_dict.items():
        template = template.replace('{%s}' % key, value)

    # Write the substituted SQL to the output file
    with open(output_path, 'w') as output_file:
        output_file.write(template)

def start_docker_container(testing=False):
    # Define the docker-compose command
    compose_command = ['docker-compose']

    # Add the appropriate flags based on the testing flag
    if testing:
        compose_command.extend(['-f', 'testing-compose.yaml',])
    else:
        compose_command.extend(['-f', 'docker-compose.yml'])
    # Add the remaining arguments for starting the container
    compose_command.extend(['up', '--build', '--force-recreate'])
    compose_command += testing *  ['--abort-on-container-exit', '--exit-code-from', 'flask-app']
    # Run the docker-compose command
    run(compose_command)

def stop_docker_container():
    # Run docker-compose down command    
    compose_command = ['docker-compose']

    # Add the appropriate flags based on the testing flag
    if testing:
        compose_command.extend(['-f', 'testing-compose.yaml'])
    else:
        compose_command.extend(['-f', 'docker-compose.yml'])
    # Add the remaining arguments for starting the container
    compose_command.extend(['down', '--volumes', '--remove-orphans'])
    run(compose_command)

if __name__ == '__main__':
    template_path_1 = 'templates/template.sql'
    output_path_1 = 'init-scripts/init.sql'
    template_path_2 = 'templates/compose.yml'
    output_path_2 = 'docker-compose.yml'

    # Check if the -t flag is provided
    if '-t' in argv:
        testing = True
    else:
        testing = False
    
    substitute_variables(template_path_1, output_path_1, testing)
    substitute_variables(template_path_2, output_path_2, testing)
    # Start the Docker container
    try:
        start_docker_container(testing)
    except:
        pass
    
    # Stop the Docker container
    stop_docker_container()
