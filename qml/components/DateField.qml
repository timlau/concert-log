import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property alias text: field.text
    property bool clearable: false

    implicitWidth: 210
    implicitHeight: 40

    readonly property var selected: {
        const parts = field.text.split("-")
        if (parts.length !== 3)
            return null
        const year = parseInt(parts[0])
        const month = parseInt(parts[1]) - 1
        const day = parseInt(parts[2])
        if (isNaN(year) || isNaN(month) || isNaN(day))
            return null
        return { year: year, month: month, day: day }
    }

    function openPicker() {
        const parsed = new Date(field.text + "T12:00:00")
        const base = isNaN(parsed.getTime()) ? new Date() : parsed
        picker.displayMonth = base.getMonth()
        picker.displayYear = base.getFullYear()
        picker.open()
    }

    function shiftMonth(step) {
        let month = picker.displayMonth + step
        let year = picker.displayYear
        if (month < 0) {
            month = 11
            year -= 1
        } else if (month > 11) {
            month = 0
            year += 1
        }
        picker.displayMonth = month
        picker.displayYear = year
    }

    function setToday() {
        field.text = Qt.formatDate(new Date(), "yyyy-MM-dd")
        picker.close()
    }

    AppTextField {
        id: field
        anchors.fill: parent
        placeholderText: "YYYY-MM-DD"
        rightPadding: root.clearable && field.text.length > 0 ? 74 : 42
        onAccepted: root.openPicker()
    }

    Rectangle {
        visible: root.clearable && field.text.length > 0
        width: 26
        height: 28
        anchors.right: parent.right
        anchors.rightMargin: 39
        anchors.verticalCenter: parent.verticalCenter
        radius: 5
        color: clearMouse.containsMouse ? theme.hover : "transparent"

        Text {
            anchors.centerIn: parent
            text: "×"
            color: theme.foregroundMuted
            font.family: theme.fontFamily
            font.pixelSize: 14
        }

        MouseArea {
            id: clearMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: {
                field.text = ""
                field.forceActiveFocus()
            }
        }
    }

    Rectangle {
        width: 32
        height: 28
        anchors.right: parent.right
        anchors.rightMargin: 5
        anchors.verticalCenter: parent.verticalCenter
        radius: 5
        color: calendarMouse.containsMouse ? theme.hover : "transparent"

        Text {
            anchors.centerIn: parent
            text: "▦"
            color: theme.foregroundMuted
            font.family: theme.fontFamily
            font.pixelSize: 15
        }

        MouseArea {
            id: calendarMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.openPicker()
        }
    }

    Popup {
        id: picker

        property int displayMonth: 0
        property int displayYear: 0

        x: 0
        y: field.height + 6
        width: 292
        padding: 14
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            color: theme.surfaceRaised
            radius: 10
            border.width: 1
            border.color: theme.borderStrong
        }

        contentItem: Column {
            spacing: 8
            width: 264

            RowLayout {
                width: parent.width
                spacing: 4

                AppButton {
                    compact: true
                    ghost: true
                    text: "‹"
                    implicitWidth: 30
                    onClicked: root.shiftMonth(-1)
                }

                Text {
                    Layout.fillWidth: true
                    horizontalAlignment: Text.AlignHCenter
                    text: Qt.formatDate(new Date(picker.displayYear, picker.displayMonth, 1), "MMMM yyyy")
                    color: theme.foreground
                    font.family: theme.fontFamily
                    font.pixelSize: 13
                    font.weight: Font.Medium
                }

                AppButton {
                    compact: true
                    ghost: true
                    text: "›"
                    implicitWidth: 30
                    onClicked: root.shiftMonth(1)
                }
            }

            DayOfWeekRow {
                width: parent.width
                locale: Qt.locale()

                delegate: Text {
                    required property string shortName

                    width: 36
                    horizontalAlignment: Text.AlignHCenter
                    text: shortName
                    color: theme.foregroundDim
                    font.family: theme.fontFamily
                    font.pixelSize: 9
                }
            }

            MonthGrid {
                id: grid

                width: 264
                height: 190
                month: picker.displayMonth
                year: picker.displayYear
                spacing: 2
                locale: Qt.locale()

                delegate: Rectangle {
                    id: dayCell

                    required property var model

                    implicitWidth: 36
                    implicitHeight: 30
                    radius: 5

                    readonly property bool inMonth: model.month === grid.month
                    readonly property bool isPicked: root.selected !== null
                                                     && model.day === root.selected.day
                                                     && model.month === root.selected.month
                                                     && model.year === root.selected.year

                    color: isPicked ? theme.accent : dayMouse.containsMouse ? theme.hover : "transparent"
                    opacity: inMonth ? 1 : 0.16

                    Text {
                        anchors.centerIn: parent
                        text: model.day
                        color: dayCell.isPicked ? theme.onAccent
                                                : model.today ? theme.accent : theme.foreground
                        font.family: theme.fontFamily
                        font.pixelSize: 12
                        font.weight: model.today ? Font.DemiBold : Font.Normal
                    }

                    MouseArea {
                        id: dayMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            field.text = Qt.formatDate(model.date, "yyyy-MM-dd")
                            picker.close()
                        }
                    }
                }
            }

            RowLayout {
                width: parent.width

                AppButton {
                    compact: true
                    ghost: true
                    text: "Today"
                    onClicked: root.setToday()
                }

                Item { Layout.fillWidth: true }

                AppButton {
                    compact: true
                    ghost: true
                    text: "Close"
                    onClicked: picker.close()
                }
            }
        }
    }
}
