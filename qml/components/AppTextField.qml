import QtQuick
import QtQuick.Controls

TextField {
    id: control

    property bool invalid: false

    implicitHeight: 40
    leftPadding: 12
    rightPadding: 12
    topPadding: 0
    bottomPadding: 0
    selectByMouse: true
    color: theme.foreground
    placeholderTextColor: theme.foregroundDim
    selectionColor: theme.accent
    selectedTextColor: theme.onAccent
    verticalAlignment: TextInput.AlignVCenter

    font.family: theme.fontFamily
    font.pixelSize: 13

    background: Rectangle {
        color: theme.inputBackground
        radius: 7
        border.width: 1
        border.color: control.invalid
                      ? theme.red
                      : control.activeFocus ? theme.accent : theme.border
        Behavior on border.color {
            ColorAnimation { duration: 120 }
        }
    }
}
