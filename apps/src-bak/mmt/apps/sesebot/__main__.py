from confctl import util

parser = util.get_argparser()
parser.add_argument('module', type=str, help="module to run")
args = parser.parse_args()
util.init_config(args)
util.init_loguru_loggers("sesebot/logs")

if "pixiv_scraper" == args.module:
    from .pixiv_scraper import main

    main()
elif "sesebot" == args.module:
    from .bot import main

    main()
else:
    exit(1)
