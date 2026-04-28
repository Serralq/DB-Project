{
  pkgs,
  lib,
  config,
  inputs,
  ...
}:

{
  packages = [
    pkgs.python313
    pkgs.libmysqlclient
    pkgs.python313Packages.mariadb
    pkgs.python313Packages.pytest
  ];
  services.mysql = {
    enable = true;
    package = pkgs.mariadb;
  };
}
