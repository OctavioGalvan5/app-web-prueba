{ pkgs }: {
  deps = [
    pkgs.glibcLocales
    pkgs.python311
    pkgs.replitPackages.python311Packages.google-generativeai
  ];
}