package main

import (
	"fmt"
	"github.com/alexflint/go-arg"
	"github.com/sakkyoi/ncp-downloader/config"
)

func main() {
	var args config.Args

	arg.MustParse(&args)

	fmt.Printf("Query: %s\n", args.Query)
}
