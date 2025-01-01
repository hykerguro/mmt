import litter
from confctl import util, config


def main():
    while (line := input("<<< ")).strip() != 'q':
        if line.startswith('it|'):
            parts = line.split('|')
            if len(parts) == 3:
                n = None
                channel = parts[1]
                data = parts[2]
            elif len(parts) == 4:
                n = int(parts[1])
                channel = parts[2]
                data = parts[3]
            else:
                print("error")
                continue
            for resp in litter.iter_request(channel, data, n=n):
                print(">>>", resp)
        else:
            channel, data = line.split("|", maxsplit=1)
            resp = litter.request(channel, data)
            print(">>>", resp)


if __name__ == '__main__':
    util.default_arg_config_loggers()
    host, port = config.get("redis/host"), config.get("redis/port")
    litter.connect(host, port, "req_client")
    main()
