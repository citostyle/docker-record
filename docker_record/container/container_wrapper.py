import os
from .instrumented_container import InstrumentedContainer

class ContainerWrapper:
    def __init__(self, container: InstrumentedContainer):
        self.container = container

    def start_container(self):
        # construct the bash script that will instrument the user's session
        instrumentation = self.get_instrumentation_sequence()
        record_template = self.get_record_template()
        record_command = record_template.format(instrumentation=instrumentation.replace('\n', ' '))

        os.execlp('docker', 'docker', 'exec', '-ti', self.container.container_name, 'bash', '-c', record_command)

    def get_record_template(self):
        return """bash --init-file <(echo '{instrumentation}')"""

    def get_instrumentation_sequence(self):
        session_root = self.container.SESSION_PATH
        labels = {'cmd': self.container.COMMANDS_FILE,
                  'pwd': self.container.WORKDIR_FILE,
                  'env': self.container.ENVIRONMENT_FILE,
                  'diff_trigger': self.container.DIFF_TRIGGER_FILE
                 }

        # bug in prompt_command --> prints multiple things into diff_trigger
        # if some output makes the promp appear multiple times,
        # even though it's the same command, we probably need to check the line numbers here to avoid duplication
        return '''
        SESSION_ROOT={session_root};
        mkdir -p $SESSION_ROOT;
        function __instrument() {
          if [[ ! $BASH_COMMAND =~ "{diff_trigger}" ]]; then
            echo $BASH_COMMAND >> $SESSION_ROOT/{cmd} &&
            echo $PWD >> $SESSION_ROOT/{pwd} &&
            echo $(export | tr "\\n" ";") >> $SESSION_ROOT/{env} ||
            exit;
          fi
        };

        shopt -s extdebug;
        trap __instrument DEBUG;

        PROMPT_COMMAND="tail -n 1 $SESSION_ROOT/{cmd} >> $SESSION_ROOT/{diff_trigger}"
        '''.format(session_root=session_root,
                   diff_trigger=labels['diff_trigger'],
                   cmd=labels['cmd'],
                   pwd=labels['pwd'],
                   env=labels['env'])


class STraceContainerWrapper(ContainerWrapper):
    def __init__(self, container_name):
        # Assumes the base image already has STrace baked in
        # (in Ubuntu: apt-get -y --no-install-recommends install strace)
        #TODO: check whether strace is present in base image
        super(STraceContainerWrapper, self).__init__(container_name)

    def get_record_template(self):
        #RECORD_TEMPLATE_PER_PROCESS_STRACE = """strace -o /tmp/record/traces/trace.log -ff -e trace=openat bash --init-file <(echo '{instrumentation}')"""
        return """strace -o /tmp/record/traces/trace.log -f -e trace=openat bash --init-file <(echo '{instrumentation}')"""