package main

import (
	"errors"
	"fmt"
	"github.com/alexflint/go-arg"
	"github.com/charmbracelet/log"
	"github.com/sakkyoi/ncp-downloader/config"
	"github.com/sakkyoi/ncp-downloader/downloader"
	"github.com/sakkyoi/ncp-downloader/util"
	"os"
)

func main() {
	log.SetReportTimestamp(false) // default to disable report timestamp

	// parse command line arguments
	var args config.Args
	p, err := arg.NewParser(arg.Config{}, &args)
	if err != nil {
		log.Fatal(err)
	}

	err = p.Parse(os.Args[1:])
	switch {
	case errors.Is(err, arg.ErrHelp):
		p.WriteHelp(os.Stdout)
		os.Exit(0)
	case errors.Is(err, arg.ErrVersion):
		fmt.Println(args.Version())
		os.Exit(0)
	case err == nil:
		// do nothing
	default:
		log.Fatal(err)
	}

	// config logger
	log.SetReportTimestamp(args.LogTimestamp)
	log.SetLevel(args.LogLevel.GetLevel())

	log.Debug(nil, "args", args)

	// build downloader
	queryParser := util.NewQueryParser(args.Query)
	downloader.BuildDownloader(queryParser, args).Start()
}
