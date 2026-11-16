import QtQuick

Rectangle {
    id: root

    property string label: ""
    property color textColor: theme.accent
    property color fillColor: theme.accentSoft
    property color lineColor: theme.accentBorder

    implicitWidth: badgeText.implicitWidth + 14
    implicitHeight: 17
    radius: 8
    color: root.fillColor
    border.width: 1
    border.color: root.lineColor

    Text {
        id: badgeText
        anchors.centerIn: parent
        text: root.label
        color: root.textColor
        font.family: theme.fontFamily
        font.pixelSize: 8
        font.weight: Font.DemiBold
        font.letterSpacing: 1.0
    }
}
