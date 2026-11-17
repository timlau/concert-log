import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "components"
import "dialogs"

ApplicationWindow {
    id: window

    width: 1180
    height: 790
    minimumWidth: 940
    minimumHeight: 660
    visible: true
    title: "Concert Log"
    color: theme.background

    property int selectedId: -1
    property var selected: null
    property string toastText: ""

    function selectConcert(show) {
        selectedId = show ? show.id : -1
        selected = show
    }

    function refreshSelection() {
        if (selectedId < 0) {
            selected = null
            return
        }
        const shows = backend.concerts
        for (let i = 0; i < shows.length; ++i) {
            if (shows[i].id === selectedId) {
                selected = shows[i]
                return
            }
        }
        selected = null
        selectedId = -1
    }

    function afterSave(concertId) {
        selectedId = concertId
        refreshSelection()
    }

    function openAdd() {
        concertDialog.openFor(null)
    }

    function selectFirst() {
        if (backend.concerts.length > 0)
            selectConcert(backend.concerts[0])
    }

    function openEdit() {
        if (selected)
            concertDialog.openFor(selected)
    }

    function openSetlist() {
        if (selected && selected.setlistImage.length > 0) {
            setlistViewer.source = selected.setlistImage
            setlistViewer.open()
        }
    }

    function showToast(message) {
        toastText = message
        toastTimer.restart()
    }

    Connections {
        target: backend

        function onConcertsChanged() {
            window.refreshSelection()
        }
    }

    Shortcut {
        sequence: "Ctrl+N"
        onActivated: window.openAdd()
    }

    Shortcut {
        sequence: "Ctrl+F"
        onActivated: searchField.forceActiveFocus()
    }

    Shortcut {
        sequence: "Ctrl+E"
        onActivated: window.openEdit()
    }

    background: Rectangle {
        gradient: Gradient {
            GradientStop { position: 0.0; color: theme.background }
            GradientStop { position: 1.0; color: theme.backgroundDeep }
        }
    }

    Timer {
        id: toastTimer
        interval: 3200
        onTriggered: window.toastText = ""
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ---------------------------------------------------------------- header

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 88

            Rectangle {
                anchors.top: parent.top
                width: parent.width
                height: 1
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "transparent" }
                    GradientStop { position: 0.28; color: theme.accent }
                    GradientStop { position: 0.68; color: theme.magenta }
                    GradientStop { position: 1.0; color: "transparent" }
                }
                opacity: 0.7
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 24
                spacing: 12

                ColumnLayout {
                    spacing: 5

                    RowLayout {
                        spacing: 9

                        Rectangle {
                            width: 8
                            height: 8
                            radius: 2
                            color: theme.accent
                        }

                        Text {
                            text: "CONCERT LOG"
                            color: theme.foreground
                            font.family: theme.fontFamily
                            font.pixelSize: 18
                            font.weight: Font.DemiBold
                            font.letterSpacing: 2.6
                        }
                    }

                    Text {
                        text: backend.stats.shows + " SHOWS   ·   "
                              + backend.stats.bands + " ARTISTS   ·   "
                              + backend.stats.venues + " VENUES"
                        color: theme.foregroundDim
                        font.family: theme.fontFamily
                        font.pixelSize: 10
                        font.letterSpacing: 1.1
                    }
                }

                Item { Layout.fillWidth: true }

                AppTextField {
                    id: searchField
                    Layout.preferredWidth: 250
                    Layout.maximumWidth: 320
                    placeholderText: "Search bands, events, venues…"
                    onTextChanged: backend.setSearch(text)
                }

                AppButton {
                    text: "Artists"
                    ghost: true
                    onClicked: bandsDialog.open()
                }

                AppButton {
                    text: "+  Add show"
                    primary: true
                    onClicked: window.openAdd()
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: theme.border
        }

        // ------------------------------------------------------------------ body

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: 22
            Layout.rightMargin: 22
            Layout.topMargin: 18
            Layout.bottomMargin: 6
            spacing: 16

            // --------------------------------------------------------- show list

            Rectangle {
                Layout.preferredWidth: 410
                Layout.fillHeight: true
                radius: 12
                color: theme.surface
                border.width: 1
                border.color: theme.border
                clip: true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 46

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 16
                            anchors.rightMargin: 16
                            spacing: 8

                            Text {
                                text: "SHOWS"
                                color: theme.foregroundMuted
                                font.family: theme.fontFamily
                                font.pixelSize: 9
                                font.letterSpacing: 1.6
                            }

                            Rectangle {
                                width: countLabel.implicitWidth + 14
                                height: 18
                                radius: 9
                                color: theme.accentSoft

                                Text {
                                    id: countLabel
                                    anchors.centerIn: parent
                                    text: backend.search.length > 0
                                          ? backend.concerts.length
                                          : backend.stats.shows
                                    color: theme.accent
                                    font.family: theme.fontFamily
                                    font.pixelSize: 9
                                    font.weight: Font.DemiBold
                                }
                            }

                            Item { Layout.fillWidth: true }

                            Text {
                                text: backend.search.length > 0 ? "FILTERED" : "NEWEST FIRST"
                                color: theme.foregroundDim
                                font.family: theme.fontFamily
                                font.pixelSize: 9
                                font.letterSpacing: 1.1
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        height: 1
                        color: theme.border
                    }

                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        ListView {
                            id: showList

                            anchors.fill: parent
                            clip: true
                            model: backend.concerts
                            spacing: 2
                            topMargin: 4
                            bottomMargin: 10
                            boundsBehavior: Flickable.StopAtBounds

                            section.property: "year"
                            section.criteria: ViewSection.FullString

                            section.delegate: Item {
                                width: ListView.view.width
                                height: 34

                                Text {
                                    anchors.left: parent.left
                                    anchors.leftMargin: 16
                                    anchors.bottom: parent.bottom
                                    anchors.bottomMargin: 4
                                    text: section
                                    color: theme.accent
                                    font.family: theme.fontFamily
                                    font.pixelSize: 10
                                    font.letterSpacing: 1.7
                                    font.weight: Font.DemiBold
                                    opacity: 0.85
                                }

                                Rectangle {
                                    anchors.left: parent.left
                                    anchors.leftMargin: 52
                                    anchors.right: parent.right
                                    anchors.rightMargin: 16
                                    anchors.bottom: parent.bottom
                                    anchors.bottomMargin: 9
                                    height: 1
                                    color: theme.border
                                }
                            }

                            delegate: Rectangle {
                                id: showCard

                                required property var modelData

                                width: ListView.view.width - 20
                                x: 10
                                height: modelData.event.length > 0 ? 96 : 78
                                radius: 9
                                color: window.selectedId === modelData.id
                                       ? theme.selection
                                       : cardMouse.containsMouse ? theme.hover : "transparent"
                                border.width: window.selectedId === modelData.id
                                              || modelData.status !== "past" ? 1 : 0
                                border.color: window.selectedId === modelData.id
                                              ? theme.accentBorder
                                              : modelData.status === "upcoming"
                                                ? theme.accentSoft
                                                : modelData.status === "ongoing"
                                                  ? theme.successBorder
                                                  : "transparent"

                                Behavior on color {
                                    ColorAnimation { duration: 100 }
                                }

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 10
                                    anchors.rightMargin: 12
                                    anchors.topMargin: 9
                                    anchors.bottomMargin: 9
                                    spacing: 12

                                    Column {
                                        Layout.preferredWidth: 48
                                        Layout.alignment: Qt.AlignVCenter
                                        spacing: 1

                                        Text {
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            text: showCard.modelData.day
                                            color: window.selectedId === showCard.modelData.id
                                                   ? theme.accent : theme.foreground
                                            font.family: theme.fontFamily
                                            font.pixelSize: 23
                                            font.weight: Font.DemiBold
                                        }

                                        Text {
                                            anchors.horizontalCenter: parent.horizontalCenter
                                            text: showCard.modelData.weekday.toUpperCase()
                                                  + " · " + showCard.modelData.month.toUpperCase()
                                            color: theme.foregroundDim
                                            font.family: theme.fontFamily
                                            font.pixelSize: 9
                                            font.letterSpacing: 0.7
                                        }
                                    }

                                    Rectangle {
                                        Layout.fillHeight: true
                                        width: 1
                                        color: theme.border
                                    }

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        spacing: 3

                                        RowLayout {
                                            Layout.fillWidth: true
                                            spacing: 6

                                            Text {
                                                Layout.fillWidth: true
                                                text: showCard.modelData.band
                                                color: theme.foreground
                                                font.family: theme.fontFamily
                                                font.pixelSize: 14
                                                font.weight: Font.Medium
                                                elide: Text.ElideRight
                                            }

                                            StatusBadge {
                                                visible: showCard.modelData.statusLabel.length > 0
                                                label: showCard.modelData.statusLabel
                                                textColor: showCard.modelData.status === "upcoming"
                                                           ? theme.accent : theme.green
                                                fillColor: showCard.modelData.status === "upcoming"
                                                           ? theme.accentSoft : theme.successSoft
                                                lineColor: showCard.modelData.status === "upcoming"
                                                           ? theme.accentBorder : theme.successBorder
                                            }
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            visible: showCard.modelData.event.length > 0
                                            text: showCard.modelData.event.toUpperCase()
                                            color: theme.accent
                                            font.family: theme.fontFamily
                                            font.pixelSize: 9
                                            font.letterSpacing: 0.9
                                            elide: Text.ElideRight
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: showCard.modelData.place.length
                                                  ? showCard.modelData.place : "Venue not noted"
                                            color: theme.foregroundMuted
                                            font.family: theme.fontFamily
                                            font.pixelSize: 10
                                            elide: Text.ElideRight
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            visible: showCard.modelData.otherLabel.length > 0
                                            text: "with " + showCard.modelData.otherLabel
                                            color: theme.foregroundDim
                                            font.family: theme.fontFamily
                                            font.pixelSize: 10
                                            elide: Text.ElideRight
                                        }
                                    }
                                }

                                MouseArea {
                                    id: cardMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: window.selectConcert(showCard.modelData)
                                }
                            }

                            ScrollBar.vertical: ScrollBar {
                                id: listScroll

                                policy: ScrollBar.AsNeeded
                                width: 10

                                contentItem: Rectangle {
                                    implicitWidth: 4
                                    radius: 2
                                    color: theme.foregroundDim
                                    opacity: listScroll.pressed ? 0.9 : listScroll.active ? 0.55 : 0.25
                                }

                                background: Rectangle {
                                    color: "transparent"
                                }
                            }
                        }

                        ColumnLayout {
                            anchors.centerIn: parent
                            width: Math.min(parent.width - 60, 300)
                            spacing: 9
                            visible: backend.concerts.length === 0

                            Text {
                                Layout.alignment: Qt.AlignHCenter
                                text: "♪"
                                color: theme.accent
                                opacity: 0.45
                                font.family: theme.fontFamily
                                font.pixelSize: 42
                            }

                            Text {
                                Layout.fillWidth: true
                                horizontalAlignment: Text.AlignHCenter
                                text: backend.search.length > 0
                                      ? "Nothing matches that search."
                                      : "No shows logged yet."
                                color: theme.foreground
                                font.family: theme.fontFamily
                                font.pixelSize: 14
                                font.weight: Font.Medium
                            }

                            Text {
                                Layout.fillWidth: true
                                horizontalAlignment: Text.AlignHCenter
                                text: backend.search.length > 0
                                      ? "Try a band, venue, or city."
                                      : "Add the first concert you went to."
                                color: theme.foregroundMuted
                                font.family: theme.fontFamily
                                font.pixelSize: 10
                                wrapMode: Text.Wrap
                            }

                            AppButton {
                                Layout.alignment: Qt.AlignHCenter
                                Layout.topMargin: 2
                                visible: backend.search.length === 0
                                text: "+  Add show"
                                primary: true
                                onClicked: window.openAdd()
                            }
                        }
                    }
                }
            }

            // --------------------------------------------------------- show detail

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 12
                color: theme.surface
                border.width: 1
                border.color: theme.border
                clip: true

                ColumnLayout {
                    anchors.centerIn: parent
                    width: Math.min(parent.width - 80, 360)
                    spacing: 11
                    visible: window.selected === null

                    Text {
                        Layout.alignment: Qt.AlignHCenter
                        text: "♪"
                        color: theme.accent
                        opacity: 0.4
                        font.family: theme.fontFamily
                        font.pixelSize: 52
                    }

                    Text {
                        Layout.fillWidth: true
                        horizontalAlignment: Text.AlignHCenter
                        text: "Select a show"
                        color: theme.foreground
                        font.family: theme.fontFamily
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
                    }

                    Text {
                        Layout.fillWidth: true
                        horizontalAlignment: Text.AlignHCenter
                        text: backend.stats.shows === 0
                              ? "Start your concert log with the first show you remember."
                              : "Pick a concert from the list, or add a new one."
                        color: theme.foregroundMuted
                        font.family: theme.fontFamily
                        font.pixelSize: 11
                        wrapMode: Text.Wrap
                        lineHeight: 1.35
                    }

                    AppButton {
                        Layout.alignment: Qt.AlignHCenter
                        Layout.topMargin: 3
                        visible: backend.stats.shows === 0
                        text: "+  Add show"
                        primary: true
                        onClicked: window.openAdd()
                    }
                }

                Flickable {
                    id: detailFlick

                    anchors.fill: parent
                    anchors.margins: 30
                    visible: window.selected !== null
                    clip: true
                    contentWidth: width
                    contentHeight: detailColumn.implicitHeight
                    boundsBehavior: Flickable.StopAtBounds

                    ColumnLayout {
                        id: detailColumn

                        width: detailFlick.width
                        spacing: 18

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 14

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 6

                                Item {
                                    id: statusRow
                                    Layout.fillWidth: true
                                    implicitHeight: 17
                                    Layout.preferredHeight: 17

                                    Text {
                                        id: dateText
                                        anchors.left: parent.left
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: window.selected
                                              ? window.selected.dateLabel.toUpperCase() : ""
                                        color: theme.accent
                                        font.family: theme.fontFamily
                                        font.pixelSize: 9
                                        font.letterSpacing: 1.6
                                    }

                                    StatusBadge {
                                        id: statusBadge
                                        anchors.left: dateText.right
                                        anchors.leftMargin: 8
                                        anchors.verticalCenter: parent.verticalCenter
                                        visible: window.selected !== null
                                                 && window.selected.statusLabel.length > 0
                                        label: window.selected ? window.selected.statusLabel : ""
                                        textColor: window.selected
                                                   && window.selected.status === "upcoming"
                                                   ? theme.accent : theme.green
                                        fillColor: window.selected
                                                   && window.selected.status === "upcoming"
                                                   ? theme.accentSoft : theme.successSoft
                                        lineColor: window.selected
                                                   && window.selected.status === "upcoming"
                                                   ? theme.accentBorder : theme.successBorder
                                    }

                                    Text {
                                        id: hintText
                                        anchors.left: statusBadge.visible
                                                       ? statusBadge.right : dateText.right
                                        anchors.leftMargin: 8
                                        anchors.verticalCenter: parent.verticalCenter
                                        visible: window.selected !== null
                                                 && window.selected.statusHint.length > 0
                                        text: window.selected ? window.selected.statusHint : ""
                                        color: theme.foregroundMuted
                                        font.family: theme.fontFamily
                                        font.pixelSize: 9
                                        font.letterSpacing: 0.7
                                    }
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: window.selected ? window.selected.band : ""
                                    color: theme.foreground
                                    font.family: theme.fontFamily
                                    font.pixelSize: 30
                                    font.weight: Font.DemiBold
                                    wrapMode: Text.Wrap
                                    lineHeight: 1.05
                                }
                            }

                            RowLayout {
                                Layout.alignment: Qt.AlignTop
                                spacing: 8

                                AppButton {
                                    text: "Edit"
                                    ghost: true
                                    onClicked: window.openEdit()
                                }

                                AppButton {
                                    text: "Delete"
                                    ghost: true
                                    danger: true
                                    onClicked: {
                                        deleteDialog.message = "This removes “"
                                                + window.selected.band + "” on "
                                                + window.selected.dateLabel
                                                + " from your log."
                                        deleteDialog.open()
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            height: 1
                            color: theme.border
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 24

                            DetailBlock {
                                Layout.fillWidth: true
                                label: "EVENT"
                                value: window.selected ? window.selected.event : ""
                            }

                            DetailBlock {
                                Layout.fillWidth: true
                                label: "VENUE"
                                value: window.selected ? window.selected.venue : ""
                            }

                            DetailBlock {
                                Layout.fillWidth: true
                                label: "LOCATION"
                                value: window.selected ? window.selected.city : ""
                            }

                            DetailBlock {
                                Layout.fillWidth: true
                                label: "DATE"
                                value: window.selected ? window.selected.dateRange : ""
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Text {
                                text: "LINEUP"
                                color: theme.foregroundDim
                                font.family: theme.fontFamily
                                font.pixelSize: 9
                                font.letterSpacing: 1.3
                            }

                            Flow {
                                Layout.fillWidth: true
                                spacing: 6

                                Repeater {
                                    model: window.selected ? window.selected.otherBands : []

                                    delegate: Chip {
                                        required property var modelData
                                        label: modelData
                                    }
                                }
                            }

                            Text {
                                visible: window.selected
                                         && window.selected.otherBands.length === 0
                                text: "Solo show — no support acts noted."
                                color: theme.foregroundMuted
                                font.family: theme.fontFamily
                                font.pixelSize: 11
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            visible: window.selected && window.selected.notes.length > 0

                            Text {
                                text: "NOTES"
                                color: theme.foregroundDim
                                font.family: theme.fontFamily
                                font.pixelSize: 9
                                font.letterSpacing: 1.3
                            }

                            Text {
                                Layout.fillWidth: true
                                text: window.selected ? window.selected.notes : ""
                                color: theme.foregroundMuted
                                font.family: theme.fontFamily
                                font.pixelSize: 12
                                wrapMode: Text.Wrap
                                lineHeight: 1.4
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 8
                            visible: window.selected !== null
                                     && window.selected.setlistImage.length > 0

                            RowLayout {
                                spacing: 8

                                Text {
                                    text: "SETLIST PHOTO"
                                    color: theme.foregroundDim
                                    font.family: theme.fontFamily
                                    font.pixelSize: 9
                                    font.letterSpacing: 1.3
                                }

                                Text {
                                    text: "click to enlarge"
                                    color: theme.foregroundDim
                                    font.family: theme.fontFamily
                                    font.pixelSize: 9
                                    opacity: 0.7
                                }
                            }

                            Rectangle {
                                Layout.preferredWidth: 250
                                Layout.preferredHeight: 170
                                radius: 8
                                color: theme.inputBackground
                                border.width: 1
                                border.color: setlistThumbMouse.containsMouse
                                              ? theme.accentBorder : theme.border
                                clip: true

                                Image {
                                    anchors.fill: parent
                                    anchors.margins: 4
                                    source: window.selected
                                            ? window.selected.setlistImage : ""
                                    fillMode: Image.PreserveAspectFit
                                    asynchronous: true
                                    cache: false
                                }

                                MouseArea {
                                    id: setlistThumbMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: window.openSetlist()
                                }
                            }
                        }

                        Item {
                            Layout.fillWidth: true
                            height: 8
                        }
                    }
                }
            }
        }

        // ---------------------------------------------------------------- footer

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 30

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 24
                anchors.rightMargin: 24

                Text {
                    text: "CTRL+N  NEW SHOW    ·    CTRL+F  SEARCH    ·    CTRL+E  EDIT"
                    color: theme.foregroundDim
                    font.family: theme.fontFamily
                    font.pixelSize: 9
                    font.letterSpacing: 1.0
                }

                Item { Layout.fillWidth: true }
            }
        }
    }

    Rectangle {
        id: toast

        z: 100
        visible: window.toastText.length > 0
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 24
        width: Math.min(520, window.width - 80)
        height: 42
        radius: 9
        color: theme.surfaceRaised
        border.width: 1
        border.color: theme.dangerBorder

        Text {
            anchors.fill: parent
            anchors.leftMargin: 14
            anchors.rightMargin: 14
            verticalAlignment: Text.AlignVCenter
            text: window.toastText
            color: theme.foreground
            font.family: theme.fontFamily
            font.pixelSize: 11
            elide: Text.ElideRight
        }
    }

    ConcertDialog {
        id: concertDialog
        objectName: "concertDialog"
        parent: Overlay.overlay
        onSaved: function (concertId) { window.afterSave(concertId) }
    }

    BandsDialog {
        id: bandsDialog
        objectName: "bandsDialog"
        parent: Overlay.overlay
    }

    ConfirmDialog {
        id: deleteDialog
        parent: Overlay.overlay
        titleText: "Delete this show?"
        confirmLabel: "Delete"
        onConfirmed: {
            if (!window.selected)
                return
            const concertId = window.selected.id
            const result = backend.deleteConcert(concertId)
            if (!result.ok) {
                window.showToast(result.error)
            } else {
                window.selected = null
                window.selectedId = -1
            }
        }
    }

    Popup {
        id: setlistViewer
        objectName: "setlistViewer"

        property string source: ""

        parent: Overlay.overlay
        modal: true
        focus: true
        anchors.centerIn: parent
        width: Math.min(window.width - 80, 980)
        height: Math.min(window.height - 80, 900)
        padding: 0
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        Overlay.modal: Rectangle {
            color: theme.scrim
        }

        background: Rectangle {
            color: theme.surfaceRaised
            radius: 12
            border.width: 1
            border.color: theme.borderStrong
        }

        contentItem: Item {
            Image {
                anchors.fill: parent
                anchors.margins: 16
                source: setlistViewer.source
                fillMode: Image.PreserveAspectFit
                asynchronous: true
                cache: false
            }

            Rectangle {
                width: 30
                height: 30
                radius: 15
                anchors.top: parent.top
                anchors.right: parent.right
                anchors.margins: 10
                color: closeSetlistMouse.containsMouse
                       ? theme.hover : theme.surface
                border.width: 1
                border.color: theme.border

                Text {
                    anchors.centerIn: parent
                    text: "×"
                    color: theme.foreground
                    font.family: theme.fontFamily
                    font.pixelSize: 17
                }

                MouseArea {
                    id: closeSetlistMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: setlistViewer.close()
                }
            }
        }
    }
}
