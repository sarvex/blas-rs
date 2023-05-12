#!/usr/bin/env python

from documentation import print_documentation
from function import Function, read_functions
import argparse
import os
import re

level_scalars = {
    1: ["alpha", "a", "b", "c", "s", "d1", "d2", "x1", "y1"],
    2: ["alpha", "beta"],
    3: ["alpha", "beta"],
}

def is_const(name, cty):
    return "*const" in cty

def is_mut(name, cty):
    return "*mut" in cty

def is_scalar(name, cty, f):
    return (
        "c_char" in cty or
        "c_int" in cty and (
            name in ["m", "n", "k", "kl", "ku"] or
            name.startswith("ld") or
            name.startswith("inc")
        ) or
        name in level_scalars[f.level]
    )

def translate_argument(name, cty, f):
    base = translate_type_base(cty)
    if is_const(name, cty):
        return base if is_scalar(name, cty, f) else f"&[{base}]"
    elif is_mut(name, cty):
        return f"&mut {base}" if is_scalar(name, cty, f) else f"&mut [{base}]"
    assert False, f"cannot translate `{name}: {cty}`"

def translate_type_base(cty):
    if "c_char" in cty:
        return "u8"
    elif "c_int" in cty:
        return "i32"
    elif "c_double_complex" in cty:
        return "c64"
    elif "c_float_complex" in cty:
        return "c32"
    elif "double" in cty:
        return "f64"
    elif "float" in cty:
        return "f32"

    assert False, f"cannot translate `{cty}`"

def translate_body_argument(name, rty):
    if rty == "u8":
        return f"&({name} as c_char)"

    elif rty == "i32":
        return f"&{name}"

    elif rty.startswith("f"):
        return f"&{name}"
    elif rty.startswith("&mut f"):
        return f"{name}"
    elif rty.startswith("&[f"):
        return f"{name}.as_ptr()"
    elif rty.startswith("&mut [f"):
        return f"{name}.as_mut_ptr()"

    elif rty.startswith("c"):
        return f"&{name} as *const _ as *const _"
    elif rty.startswith("&mut c"):
        return f"{name} as *mut _ as *mut _"
    elif rty.startswith("&[c"):
        return f"{name}.as_ptr() as *const _"
    elif rty.startswith("&mut [c"):
        return f"{name}.as_mut_ptr() as *mut _"

    assert False, f"cannot translate `{name}: {rty}`"

def translate_return_type(cty):
    if cty == "c_double":
        return "f64"

    elif cty == "c_float":
        return "f32"
    elif cty == "c_int":
        return "usize"
    assert False, f"cannot translate `{cty}`"

def format_header(f):
    args = format_header_arguments(f)
    if f.ret is None:
        return f"pub unsafe fn {f.name}({args})"
    else:
        return f"pub unsafe fn {f.name}({args}) -> {translate_return_type(f.ret)}"

def format_body(f):
    args = format_body_arguments(f)
    ret = format_body_return(f)
    if ret is None:
        return f"ffi::{f.name}_({args})"
    else:
        return f"ffi::{f.name}_({args}) as {ret}"

def format_header_arguments(f):
    s = ["{}: {}".format(arg[0], translate_argument(*arg, f=f)) for arg in f.args]
    return ", ".join(s)

def format_body_arguments(f):
    s = []
    for arg in f.args:
        rty = translate_argument(*arg, f=f)
        s.append(translate_body_argument(arg[0], rty))
    return ", ".join(s)

def format_body_return(f):
    if f.ret is None:
        return None

    rty = translate_return_type(f.ret)
    return None if rty.startswith("f") else rty

def prepare(level, code):
    lines = filter(lambda line: not re.match(r'^\s*//.*', line), code.split('\n'))
    lines = re.sub(r'\s+', ' ', "".join(lines)).strip().split(';')
    lines = filter(lambda line: not re.match(r'^\s*$', line), lines)
    return [Function.parse(level, line) for line in lines]

def do(functions, reference):
    for f in functions:
        if reference is not None:
            print_documentation(f, reference)
        print("\n#[inline]")
        print(format_header(f) + " {")
        print(f"    {format_body(f)}" + "\n}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sys', required=True)
    parser.add_argument('--doc')
    arguments = parser.parse_args()
    sections = read_functions(os.path.join(arguments.sys, 'src', 'lib.rs'))
    assert(len(sections) == 3)
    do(prepare(1, sections[0]), arguments.doc)
    do(prepare(2, sections[1]), arguments.doc)
    do(prepare(3, sections[2]), arguments.doc)
