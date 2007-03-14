
import dep
import util
import glob

import os

class Types:
  HEADER="buildsys/.h"
  GCC_SOURCE="buildsys/gcc"  # .c, .cpp, etc
  OBJECT="buildsys/.o"
  LINKABLE="buildsys/.a"
  BINFILE="buildsys/bin"
  SCRIPT="buildsys/script"
  DIR="buildsys/dir"
  PLACEHOLDER="buildsys/placeholder"
  MISC="buildsys/misc"
  ANY="buildsys/*"

class CompilerInfo:
  pass

class GCCCompiler(CompilerInfo):
  def __init__(self):
    self.name = "gcc"
    self.mode_dictionary = {
      "verbose": "-g -DDEBUG -DVERBOSE",
      "debug": "-g3 -DDEBUG",
      "check": "-O2 -g -DDEBUG",
      "fast": "-O2 -g -fomit-frame-pointer -DNDEBUG",
      "unsafe": "-O3 -ffast-math -g -fomit-frame-pointer -DNDEBUG",
      "profile" : "-O2 -pg -finline-limit=8 -DPROFILE -DNDEBUG",
      "small": "-Os -DNDEBUG"
    }
    self.command_from_ext = {
      "c" : "gcc %s -c %s -o %s -Wall",
      "cc" : "g++ %s -c %s -o %s -Wall -Woverloaded-virtual -fno-exceptions -Wparentheses -fno-exceptions",
      "f" : "g77 %s -c %s -o %s -Wall -Wno-uninitialized"
    }
    self.linker = "g++"
    self.lflags_start = "-lg2c -lm -lpthread -Wl,-whole-archive"
    self.lflags_end = "-Wl,-no-whole-archive"

class ICCCompiler(CompilerInfo):
  def __init__(self):
    self.name = "icc"
    self.mode_dictionary = {
      "verbose": "-g -DDEBUG -DVERBOSE",
      "debug": "-g -DDEBUG",
      "check": "-O2 -g -DDEBUG",
      "fast": "-O3 -g -fomit-frame-pointer -DNDEBUG",
      "unsafe": "-O3 -ffast-math -g -fomit-frame-pointer -DNDEBUG",
      "profile" : "-O2 -pg -finline-limit=8 -DPROFILE -DNDEBUG",
      "small": "-Os"
    }
    self.command_from_ext = {
      "c" : "icc %s -c %s -o %s",
      "cc" : "icpc %s -c %s -o %s -fno-exceptions",
      "f" : "ifort %s -c %s -o %s -Wall"
    }
    self.linker = "icpc"
    self.lflags_start = "-lm -lpthread -Wl,-whole-archive"
    self.lflags_end = "-Wl,-no-whole-archive"

class MPICompiler(CompilerInfo):
  def __init__(self):
    self.name = "mpi"
    self.mode_dictionary = {
      "verbose": "-g -DDEBUG -DVERBOSE",
      "debug": "-g -DDEBUG",
      "check": "-O2 -g -DDEBUG",
      "fast": "-O3 -g -fomit-frame-pointer -DNDEBUG",
      "unsafe": "-O3 -ffast-math -g -fomit-frame-pointer -DNDEBUG",
      "profile" : "-O2 -pg -finline-limit=8 -DPROFILE -DNDEBUG",
      "small": "-Os"
    }
    self.command_from_ext = {
      "c" : "mpicc %s -c %s -o %s",
      "cc" : "mpiCC -fno-exceptions %s -c %s -o %s",
      "f" : "mpif77 %s -c %s -o %s -Wall"
    }
    self.linker = "mpiCC"
    self.lflags_start = "-lm -lpthread -Wl,-whole-archive"
    self.lflags_end = "-Wl,-no-whole-archive"
    #self.lflags_start = "-lm -lpthread "
    #self.lflags_end = ""

compiler_choices = [GCCCompiler(), MPICompiler(), ICCCompiler()]
compilers = dict([(c.name, c) for c in compiler_choices])

class MakeBuildSys(dep.DepSys):
  """Build system.
  """
  def __init__(self, source_dir, bin_dir):
    dep.DepSys.__init__(self)
    self.source_dir = source_dir
    self.bin_dir = bin_dir
    self.entries = []
  def begin(self, state):
    return MakeBuildSysEntry(self, state)
  def add_entry(self, entry):
    self.entries.append(entry)
  def to_makefile(self):
    def shorten(fname):
      if "/bin/" in fname:
        return fname[fname.rindex("/bin/"):]
      else:
        return fname
    lines = []
    self.entries.reverse()
    i = 0
    for (outfiles, infiles, commands) in self.entries:
      i += 1
      if commands:
        lines.append("%s: %s" % (" ".join(outfiles), " ".join(infiles)))
        outfiles_short = [shorten(outfile) for outfile in outfiles]
        lines.extend(["\t@echo '... Making %s'" % (" ".join(outfiles_short))])
        lines.extend(["\t@" + c for c in commands])
      elif infiles:
        lines.append("pseudo_%d: %s" % (i, " ".join(infiles)))
        lines.extend(["\t@echo '*** Done with %s'" % (" ".join(infiles))])
    self.entries.reverse()
    lines.append("clean:")
    lines.append("\trm -rf %s" % (self.bin_dir))
    return lines

class MakeBuildSysEntry(dep.DepSysEntry):
  def __init__(self, sys, state):
    dep.DepSysEntry.__init__(self, sys, state)
    self.commands = []
  def _make_name(self, simplename, parameterization):
    # NOTE: I'm completely ignoring the file list (self.state.files)
    dirname = self.bin_dir(*parameterization)
    return os.path.join(dirname, simplename)
  def bin_dir(self, *pmz):
    def name_part(param_name):
      if param_name in pmz:
        return self.state.params[param_name]
      else:
        return "COMMON"

    allowed_sequence = ["arch", "kernel", "mode", "compiler"]
    (arch, kernel, mode, compiler) = [name_part(x) for x in allowed_sequence]
    
    for param in pmz:
      if not param in allowed_sequence:
        raise Exception("I can't deal with extra parameterization yet: '%s' not in '%s'" % (param, allowed_sequence))
    
    return os.path.join(self.sys.bin_dir, "%s_%s_%s_%s" % (arch, kernel, mode, compiler))
  def source_file(self, real_path, fake_path):
    return dep.DestFile(real_path, fake_path)
  def makefile(self):
    return self.source_file(os.path.abspath("./Makefile"), "Makefile")
  def ensure_writable(self, name):
    self.command("mkdir -p %s" % (os.path.dirname(name)))
  def command(self, str):
    self.commands.append(str)
  def end(self, files):
    infiles = {}
    for file in dep.filemap_to_files(self.state.files):
      infiles[file.name] = None
    outfiles = [file.name for (classname, file) in files]
    self.sys.add_entry((outfiles, list(infiles.keys()), self.commands))

class SourceRule(dep.Rule):
  def __init__(self, type, real_path, fake_path):
    dep.Rule.__init__(self)
    self.real_path = real_path
    self.fake_path = fake_path
    self.type = type
  def doit(self, sysentry, state, files, params):
    return [(self.type, sysentry.source_file(self.real_path, self.fake_path))]

class CompileRule(dep.Rule):
  def __init__(self, source, headers, cflags):
    dep.Rule.__init__(self, source=[source], headers=headers)
    self.cflags = cflags
  def doit(self, sysentry, state, files, params):
    compiler = compilers[params["compiler"]]
    source = files["source"].single(Types.GCC_SOURCE)
    dot = source.simplename.rindex(".")
    sourceextension = source.simplename[dot+1:]
    simplename = source.simplename[:dot] + ".o"
    object = sysentry.file("obj/" + simplename.replace("/", "_"), "arch", "kernel", "mode", "compiler")
    # TODO: -I flags
    my_includes = "-I%s -I%s" % (sysentry.bin_dir("arch", "kernel", "compiler"),
        sysentry.sys.source_dir)
    mode = params["mode"]
    my_flags = my_includes + " " + compiler.mode_dictionary[params["mode"]] + " " + self.cflags
    if not sourceextension in compiler.command_from_ext:
      raise Exception("Don't know how to compile files of type [%s]." % sourceextension)
    command_template = compiler.command_from_ext[sourceextension]
    (source_dirname, source_basename) = os.path.split(source.name)
    compile_cmd = command_template % (my_flags, source_basename, object.name)
    sysentry.command("cd " + source_dirname + " && " + compile_cmd)
    return [(Types.OBJECT, object)]

class ArchiveRule(dep.Rule):
  def __init__(self, name, objects):
    dep.Rule.__init__(self, objects=objects)
    self.name = name
  def doit(self, sysentry, state, files, params):
    objects = files["objects"].many(Types.OBJECT)
    libfile = sysentry.file("lib" + self.name + ".a", "arch", "kernel", "mode", "compiler")
    sysentry.command("ar r %s %s" % (libfile, " ".join([x.name for x in objects])))
    return [(Types.LINKABLE, libfile)]
    #return [(Types.OBJECT, object) for object in objects]

class HeaderSummaryRule(dep.Rule):
  def __init__(self, name, objects):
    dep.Rule.__init__(self, objects=objects)
    self.name = name
  def doit(self, sysentry, state, files, params):
    libfile = sysentry.file("lib" + self.name + ".h")
    sysentry.command("touch %s" % (libfile))
    return [(Types.PLACEHOLDER, libfile)]

class LibRule(dep.Rule):
  """LibRule returns all relevant archive files for this library and libraries
  it depends on.
  
  In addition, a LibRule exposes header files.
  """
  # TODO: "sources" will also natively support C++ files
  def __init__(self, name, sources, headers, deplibs, cflags = ""):
    source_rules = sources
    self.header_rules = headers
    # TODO: Be careful about depending on extra stuff?
    for dep_lib in deplibs:
      self.header_rules.append(dep_lib.header_summary_rule)
    self.header_summary_rule = HeaderSummaryRule(name, self.header_rules)
    self.compile_rules = [CompileRule(source_rule, self.header_rules, cflags)
        for source_rule in source_rules]
    self.archive_rule = ArchiveRule(name, self.compile_rules)
    dep.Rule.__init__(self, archive=[self.archive_rule], deplibs=deplibs)
  def doit(self, sysentry, state, files, params):
    return files["deplibs"].to_pairs() + files["archive"].to_pairs()

class BinRule(dep.Rule):
  def __init__(self, name, linkables):
    self.name = name
    dep.Rule.__init__(self, linkables=linkables)
  def doit(self, sysentry, state, files, params):
    compiler = compilers[params["compiler"]]
    binfile = sysentry.file(self.name, "arch", "kernel", "mode", "compiler")
    # TO-DO: Link flags necessary?
    lflags_start = compiler.lflags_start
    lflags_end = compiler.lflags_end
    cflags = compiler.mode_dictionary[params["mode"]]
    sysentry.command(compiler.linker + " -o %s %s %s %s %s" % (binfile.name, cflags,
        lflags_start, " ".join(files["linkables"].to_names()), lflags_end))
    return [(Types.BINFILE, binfile)]

class MakefileRule(dep.Rule):
  """
  Plug created so that symlinks are re-created whenever the Makefile changes.
  """
  def __init__(self):
    dep.Rule.__init__(self)
  def doit(self, sysentry, state, files, params):
    file = sysentry.makefile()
    return [(Types.MISC, file)]

class SymlinkRule(dep.Rule):
  def __init__(self, filerules, dest_dir):
    dep.Rule.__init__(self, filerules=filerules, makefile=[MakefileRule()])
    self.dest_dir = dest_dir
  def doit(self, sysentry, state, files, params):
    all = []
    pairs = files["filerules"].to_pairs()
    for (classname, file) in pairs:
      sourcename = file.name
      destname = os.path.join(self.dest_dir, os.path.basename(file.simplename))
      # the symlink's simplename will be the same as the original's
      destfile = sysentry.source_file(destname, file.simplename)
      sysentry.command("rm -f %s" % destname)
      sysentry.command("ln -s %s %s" % (sourcename, destname))
      all.append((classname, destfile))
    sysentry.command("echo '*** Created %d symlinks in %s.'" % (len(pairs), self.dest_dir))
    return all

# Parameter loader

BUILD_FILE = "build.py"

class Loader:
  """Responsible for loading build files and helping them stitch together.
  
  There are concepts of real and fake paths:
  
  - Real path: Where the file is located exactly on the file system.
  
  - Fake path: Where results generated by this file are relative to the
  build system.  If the real path is within the build directories, then
  the fake path is just the relative path from the root of the build
  system.  However, we also support building small code trees that are
  not in the build system.  In this, the "fake" path starts with "outside"
  to indicate it is outside the build system, and has the full path.
  
  Example:
  
  Say my build path is
  
    ~/fastlib/c  (this is real_rootpath)
  
  Someone wants to build ~/fastlib/c/foo/bar, the fake path is "foo/bar".
  
  But if someone wants to build ~/foo/bar, the fake path is
  "outside/home/yourname/foo/bar".
  
  
  See also ../script/fl-build.
  """
  
  def __init__(self, real_rootpath):
    self.real_root = real_rootpath.rstrip(os.sep)
    self.thebuildsys = MakeBuildSys(
        self.real_root, os.path.join(self.real_root, "bin"))
    self.loader_map = {}
  
  def pathjoin(self, left, right, defaultprefix, lsep = "/", rsep = "/"):
    def helper(left, right):
      if right and right[0] == ".":
        right_index = (right + "/").index(rsep)
        right_first = right[:right_index]
        right_rest = right[right_index+1:]
        if right_first == ".":
          return helper(left, right_rest)
        else:
          try:
            left_index = left.rindex(lsep)
          except:
            left_index = 0
          return helper(left[:left_index], right_rest)
      else:
        return left + lsep + right.replace(rsep, lsep)
    left = left.rstrip(lsep)
    right = right.rstrip(rsep)
    if not right:
      return left
    elif right[0] != ".":
      if right[0] == rsep:
        return right.replace(rsep, lsep)
      else:
        return defaultprefix + right.replace(rsep, lsep)
    else:
      return helper(left, right)
  
  def pathjoin_real(self, left, right):
    return self.pathjoin(left, right, self.real_root + "/", os.sep, "/")
  
  def pathjoin_fake(self, left, right):
    return self.pathjoin(left, right, "", "/", "/")

  def find_rule(self, rule_path, cur_real_path, cur_fake_path):
    #print "trying: %s" % fullname
    (path_rel, rule_name) = rule_path.split(":")
    
    fake_path = self.pathjoin_fake(cur_fake_path, path_rel)
    real_path = self.pathjoin_real(cur_real_path, path_rel)
    
    if not fake_path in self.loader_map:
      self.load(real_path, fake_path)
    if not rule_name in self.loader_map[fake_path]:
      raise Exception("Rule '%s' not found in '%s'." % (rule_name, real_path))
    #print "Found [%s][%s] aka [%s]" % (fullname, defaultpath, path)
    return self.loader_map[fake_path][rule_name]

  def load(self, real_path, fake_path):
    """Loads build rules, by exposing a 'register' function."""
    
    # !!!!! LOOK AT ME!  All the functions in build rules are defined here!
    
    self.loader_map[fake_path] = {}
    selfname = fake_path.split("/")[-1]
    def register(name, rule):
      if name in self.loader_map[fake_path]:
        raise Exception("Duplicate rule %s:%s" % (fake_path, name))
      self.loader_map[fake_path][name] = rule
      return rule
    def find(rule_name):
      return self.find_rule(rule_name, real_path, fake_path)
    def pathify_real(name):
      return self.pathjoin_real(real_path, name)
    def pathify_fake(name):
      return self.pathjoin_fake(fake_path, name)
    def sourcerule(type, name):
      if isinstance(name, str):
        # If there is a colon, it is a rule; otherwise, it is just a file.
        if ":" in name:
          return find(name)
        else:
          return SourceRule(type, pathify_real("./" + name), pathify_fake("./" + name))
      else:
        return name
    def sourcerules(type, names):
      return [sourcerule(type, name) for name in names]
    def lglob(mask, *exclude):
      (relpath, namemask) = os.path.split(mask)
      full_path = os.path.join(real_path, mask)
      basenames = [os.path.basename(f)
          for f in glob.glob(os.path.join(real_path, mask))]
      return [os.path.join(relpath, basename)
          for basename in basenames if not basename in exclude]
    def librule(name = selfname,
        sources = [], headers = [], deplibs = [], cflags = ""):
      return register(name, LibRule(pathify_fake(name),
          sourcerules(Types.GCC_SOURCE, sources),
          sourcerules(Types.HEADER , headers),
          sourcerules(Types.LINKABLE, deplibs),
          cflags))
    def unittest(name = selfname + "_unittest",
        lib = ":" + selfname,
        sources = []):
      """Unit tests for the purpose of testing one library.
      
      All .c or .cc files are compiled and run as unit tests.
      
      (TODO: Unit test framework)
      """
      assert sources
    def inttest(name = selfname + "_inttest",
        libs = [],
        sources = []):
      """Integration tests for testing multiple libraries.
      """
      assert libs
      assert sources
    def binrule(name, linkables = [], sources = [], headers = [], cflags = ""):
      # (source, headers, cflags)
      if sources:
        lib = librule(name = name + "__auto",
            sources = sources, headers = headers, deplibs = linkables,
            cflags = cflags)
        linkables = linkables + [lib]
      register(name, BinRule(name, sourcerules(Types.LINKABLE, linkables)))
    build_file_path = os.path.join(real_path, BUILD_FILE)
    print "... Reading %s" % (build_file_path)
    text = util.readfile(build_file_path)
    exec text in {"register" : register, "Types" : Types,
                  "find" : find, "dep" : dep, "lglob" : lglob,
                  "sourcerule" : sourcerule, "sourcerules" : sourcerules,
                  "librule" : librule, "binrule" : binrule}

