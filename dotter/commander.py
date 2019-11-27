import re


class Commander:
    CMD_METHOD_ARGS = re.compile(r'^cmd__([\w_]+)__args$')
    CMD_METHOD = re.compile(r'^cmd__([\w_]+)$')

    def __init__(self, parser=None):
        self.global_args = None
        self.args = None
        self.commands = self.__get_commands()
        if parser is not None:
            self.register_args(parser)

    def register_args(self, parser):
        getattr(self, '_global__args', lambda p: None)(parser)

        sparser = parser.add_subparsers(dest='command')
        for name, info in self.commands.items():
            method = getattr(self, info['args'])
            if callable(method):
                cmd_parser = sparser.add_parser(name)
                method(cmd_parser)

        self.args = parser.parse_args()

        return parser

    def run(self, parser, args):
        cmd = args.command
        method_name = self.commands.get(cmd, {}).get('cmd', None)
        if method_name:
            return getattr(self, method_name)(parser, args)
        return 0

    def __get_commands(self):
        commands = {}

        def update_commands(name, key, m):
            entry = commands.get(name, {})
            entry[key] = m
            commands[name] = entry

        for m in dir(self):
            match_args = self.CMD_METHOD_ARGS.match(m)
            match_cmd = self.CMD_METHOD.match(m)
            if match_args:
                update_commands(match_args.group(1), 'args', m)
            elif match_cmd:
                update_commands(match_cmd.group(1), 'cmd', m)
        return commands
