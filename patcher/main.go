// Command kami-zh-patch turns an installed DOS/V copy of 神々の大地 (KOEI,
// 1993) into the Traditional Chinese version.
//
// The patch (kami-zh.kzp, written by tools/mkpatch.py) is embedded. The
// original folder is never modified: everything is copied to a sibling
// folder KAMI_ZH and the changed files are rebuilt there.
//
//	kami-zh-patch [game folder]
//
// Without an argument it looks next to the executable and in the current
// directory, for a folder holding MAIN.EXE or a KAMI subfolder.
package main

import (
	"bufio"
	"bytes"
	"crypto/sha256"
	_ "embed"
	"encoding/binary"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

//go:embed kami-zh.kzp
var patchData []byte

const outName = "KAMI_ZH"

type filePatch struct {
	name             string
	srcSize, dstSize uint32
	srcSum, dstSum   [32]byte
	ops              []byte
	opCount          uint32
}

func parse(data []byte) ([]filePatch, error) {
	r := bytes.NewReader(data)
	magic := make([]byte, 4)
	r.Read(magic)
	if string(magic) != "KZP1" {
		return nil, errors.New("內建的修補資料損毀")
	}
	var count uint16
	binary.Read(r, binary.LittleEndian, &count)
	var files []filePatch
	for i := 0; i < int(count); i++ {
		var f filePatch
		n, _ := r.ReadByte()
		name := make([]byte, n)
		r.Read(name)
		f.name = string(name)
		binary.Read(r, binary.LittleEndian, &f.srcSize)
		r.Read(f.srcSum[:])
		binary.Read(r, binary.LittleEndian, &f.dstSize)
		r.Read(f.dstSum[:])
		binary.Read(r, binary.LittleEndian, &f.opCount)
		start := len(data) - r.Len()
		for j := uint32(0); j < f.opCount; j++ {
			kind, _ := r.ReadByte()
			if kind == 0 {
				r.Seek(8, 1)
			} else {
				var length uint32
				binary.Read(r, binary.LittleEndian, &length)
				r.Seek(int64(length), 1)
			}
		}
		f.ops = data[start : len(data)-r.Len()]
		files = append(files, f)
	}
	return files, nil
}

func (f filePatch) apply(src []byte) []byte {
	out := make([]byte, 0, f.dstSize)
	ops := f.ops
	for j := uint32(0); j < f.opCount; j++ {
		kind := ops[0]
		if kind == 0 {
			off := binary.LittleEndian.Uint32(ops[1:])
			length := binary.LittleEndian.Uint32(ops[5:])
			out = append(out, src[off:off+length]...)
			ops = ops[9:]
		} else {
			length := binary.LittleEndian.Uint32(ops[1:])
			out = append(out, ops[5:5+length]...)
			ops = ops[5+length:]
		}
	}
	return out
}

// findFile matches a name case-insensitively, as DOS file names are.
func findFile(dir, name string) (string, bool) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return "", false
	}
	for _, e := range entries {
		if !e.IsDir() && strings.EqualFold(e.Name(), name) {
			return filepath.Join(dir, e.Name()), true
		}
	}
	return "", false
}

func findGame(args []string) (string, error) {
	var tries []string
	if len(args) > 0 {
		tries = append(tries, args[0], filepath.Join(args[0], "KAMI"))
	} else {
		if exe, err := os.Executable(); err == nil {
			dir := filepath.Dir(exe)
			tries = append(tries, dir, filepath.Join(dir, "KAMI"))
		}
		if wd, err := os.Getwd(); err == nil {
			tries = append(tries, wd, filepath.Join(wd, "KAMI"))
		}
	}
	for _, dir := range tries {
		if _, ok := findFile(dir, "MAIN.EXE"); ok {
			return filepath.Abs(dir)
		}
	}
	return "", errors.New("找不到遊戲資料夾（含 MAIN.EXE 的 KAMI 資料夾）。\n" +
		"請把本程式放在 KAMI 資料夾裡或旁邊再執行，或把 KAMI 資料夾拖到本程式上。")
}

func run(args []string) error {
	files, err := parse(patchData)
	if err != nil {
		return err
	}
	game, err := findGame(args)
	if err != nil {
		return err
	}
	fmt.Println("遊戲資料夾：", game)

	// Check every file before writing anything.
	sources := map[string][]byte{}
	for _, f := range files {
		path, ok := findFile(game, f.name)
		if !ok {
			return fmt.Errorf("缺少 %s", f.name)
		}
		src, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		switch sha256.Sum256(src) {
		case f.srcSum:
			sources[f.name] = src
		case f.dstSum:
			return fmt.Errorf("%s 已經是中文版，不需要再修補", f.name)
		default:
			return fmt.Errorf("%s 與支援的原版不同（可能是其他版本或已被修改），無法修補", f.name)
		}
	}

	out := filepath.Join(filepath.Dir(game), outName)
	if strings.EqualFold(filepath.Clean(out), filepath.Clean(game)) {
		out = filepath.Join(filepath.Dir(game), outName+"2")
	}
	if _, err := os.Stat(out); err == nil {
		return fmt.Errorf("%s 已存在，請先刪除或改名後再執行", out)
	}
	if err := os.Mkdir(out, 0o755); err != nil {
		return err
	}

	entries, err := os.ReadDir(game)
	if err != nil {
		return err
	}
	self, _ := os.Executable()
	for _, e := range entries {
		if e.IsDir() || filepath.Join(game, e.Name()) == self {
			continue
		}
		data, err := os.ReadFile(filepath.Join(game, e.Name()))
		if err != nil {
			return err
		}
		if err := os.WriteFile(filepath.Join(out, e.Name()), data, 0o644); err != nil {
			return err
		}
	}
	for _, f := range files {
		dst := f.apply(sources[f.name])
		if sha256.Sum256(dst) != f.dstSum {
			return fmt.Errorf("%s 修補結果不正確", f.name)
		}
		path, _ := findFile(out, f.name)
		if err := os.WriteFile(path, dst, 0o644); err != nil {
			return err
		}
		fmt.Println("  已修補", f.name)
	}
	fmt.Println("完成！中文版在：", out)
	fmt.Println("原本的資料夾沒有任何變動。")
	return nil
}

func main() {
	setupConsole()
	fmt.Println("《神々の大地 ～古事記外伝～》繁體中文化修補程式")
	fmt.Println()
	err := run(os.Args[1:])
	if err != nil {
		fmt.Println("錯誤：", err)
	}
	fmt.Println()
	fmt.Print("按 Enter 結束…")
	bufio.NewReader(os.Stdin).ReadString('\n')
	if err != nil {
		os.Exit(1)
	}
}
