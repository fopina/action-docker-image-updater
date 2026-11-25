import os


def set_github_action_output(output_name, output_value):
    output_file = os.getenv('GITHUB_OUTPUT')
    line = f'{output_name}={output_value}\n'

    if output_file:
        with open(output_file, 'a') as f:
            f.write(line)
    else:
        # to be able to use from terminal
        print(line, end=None)
