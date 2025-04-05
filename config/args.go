package config

import "github.com/charmbracelet/log"

type Level log.Level

func (l *Level) UnmarshalText(text []byte) error {
	level, err := log.ParseLevel(string(text))
	if err != nil {
		return err
	}

	*l = Level(level)

	return nil
}

func (l *Level) GetLevel() log.Level {
	return log.Level(*l)
}

type Args struct {
	Query        string `arg:"positional,required" help:"URL of the video or channel"`
	Output       string `arg:"-o,--output" help:"Output path" default:"output"`
	LogTimestamp bool   `arg:"-t,--timestamp" help:"Add timestamp to the log" default:"false"`
	LogLevel     Level  `arg:"-l,--log-level" help:"Log level" default:"info"`
}

func (Args) Version() string {
	return "0.0.0" // TODO: implement versioning
}
