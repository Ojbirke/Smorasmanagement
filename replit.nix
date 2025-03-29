{pkgs}: {
  deps = [
    pkgs.postgresql
    pkgs.gettext
    pkgs.freetype
    pkgs.glibcLocales
  ];
}
