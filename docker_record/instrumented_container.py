import os

class InstrumentedContainer:
    def __init__(self, container_name):
        self.container_name = container_name


    def start(self):
        # construct the bash script that will instrument the user's session
        RECORD_TEMPLATE = """bash --init-file <(echo '{instrumentation}')"""
        INSTRUMENTATION = '''
        SESSION_ROOT=/tmp/record;
        EXIT_SIGNAL="!EXIT!"
        mkdir -p $SESSION_ROOT;
        function __instrument() {
          if [[ ! $BASH_COMMAND =~ "diff_trigger" ]]; then
            echo $EUID >> $SESSION_ROOT/euid &&
            echo $BASH_COMMAND >> $SESSION_ROOT/cmd &&
            echo $PWD >> $SESSION_ROOT/pwd &&
            echo $(export | tr "\\n" ";") >> $SESSION_ROOT/env ||
            exit;
          fi
        };

        shopt -s extdebug;
        trap __instrument DEBUG;

        PROMPT_COMMAND="tail -n 1 $SESSION_ROOT/cmd >> $SESSION_ROOT/diff_trigger"
        '''

        RECORD_COMMAND = RECORD_TEMPLATE.format(instrumentation=INSTRUMENTATION.replace('\n', ' '))

        os.execlp('docker', 'docker', 'exec', '-ti', self.container_name, 'bash', '-c', RECORD_COMMAND)





