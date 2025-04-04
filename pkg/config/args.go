package config

type Args struct {
	Query  string `arg:"positional,required" help:"URL of the video or channel"`
	Output string `arg:"-o,--output" help:"Output path" default:"output"`
}

func (Args) Version() string {
	return "0.0.0" // TODO: implement versioning
}
