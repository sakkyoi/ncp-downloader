package main

import (
	"errors"
	"github.com/alexflint/go-arg"
	"github.com/charmbracelet/log"
	"github.com/sakkyoi/ncp-downloader/config"
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
		log.Info("", "version", args.Version())
		os.Exit(0)
	case err == nil:
		// do nothing
	default:
		log.Fatal(err)
	}

	// config logger
	log.SetReportTimestamp(args.LogTimestamp)
	log.SetLevel(args.LogLevel.GetLevel())
}
