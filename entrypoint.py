#!/usr/bin/env -S python3 -u
import os

import requests


# Set the output value by writing to the outputs in the Environment File, mimicking the behavior defined here:
# https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-an-output-parameter
def set_github_action_output(output_name, output_value):
    output_file = os.getenv('GITHUB_OUTPUT')
    line = f'{output_name}={output_value}\n'

    if output_file:
        with open(output_file, 'a') as f:
            f.write(line)
    else:
        # to be able to use from terminal
        print(line, end=None)


def find_a_joke():
    r = requests.get('https://v2.jokeapi.dev/joke/Any?type=single')
    r.raise_for_status()
    return r.json()['joke']


def main():
    number_one = os.getenv('INPUT_NUMBER-ONE', '')
    number_two = os.getenv('INPUT_NUMBER-TWO', '')

    if number_one.isdigit() and number_two.isdigit():
        output = int(number_one) + int(number_two)
    else:
        output = find_a_joke().replace('\n', ' ')

    set_github_action_output('sum', output)


if __name__ == '__main__':
    main()
