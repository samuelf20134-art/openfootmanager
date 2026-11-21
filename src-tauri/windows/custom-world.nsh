!macro NSIS_HOOK_POSTINSTALL
  SetShellVarContext current
  CreateDirectory "$APPDATA\openfootmanager\packages"
  CopyFiles /SILENT "$INSTDIR\data\custom-world.ofm" "$APPDATA\openfootmanager\packages\custom-world.ofm"
!macroend
