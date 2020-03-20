from threading import Thread

from flask import Flask, request, jsonify

from driveAPI import get_video_by_name
from calendarAPI import get_events
from merge import hstack_camera_and_screen, process_wait
from models import Session, Record, Room

from datetime import date

app = Flask("NVR_VIDEO_MERGE")


@app.route('/', methods=["GET"])
def main():
    return "Merge server v2.0", 200


@app.route('/gcalendar-webhook', methods=["POST"])
def gcalendar_webhook():
    json_data = request.get_json()
    calendar_id = json_data['calendar_id']

    events = get_events(calendar_id)

    session = Session()
    room = session.query(Room).filter(Room.calendar == calendar_id).first()
    records = session.query(Record).filter(
        Record.room_name == room.name, Record.event_id != None).all()
    calendar_events = set(events.keys())
    db_events = {record.event_id for record in records}

    new_events = calendar_events - db_events
    deleted_events = db_events - calendar_events
    events_to_check = calendar_events & db_events

    for event_id in deleted_events:
        record = session.query(Record).filter(
            Record.event_id == event_id).first()
        session.delete(record)

    for event_id in new_events:
        event = events[event_id]
        start_date = event['start']['dateTime'].split('T')[0]
        end_date = event['end']['dateTime'].split('T')[0]

        if start_date != end_date:
            continue

        new_record = Record()
        new_record.update(**event, room_name=room.name)
        session.add(new_record)

    for event_id in events_to_check:
        event = events[event_id]
        if date.today().isoformat() != event['updated'].split('T')[0]:
            continue

        record = session.query(Record).filter(
            Record.event_id == event_id).first()
        record.update(**event, room_name=room.name)

    session.commit()
    session.close()

    return f"Room {room.name}: calendar events patched", 200


@app.route('/merge', methods=["POST"])
def start_new_merge():
    # TODO: переделать весь метод
    json = request.get_json(force=True)
    if len(json['cameras']) != len(json['screens']):
        resp = {'error': 'The number of camera and screen files should be equal'}
        return jsonify(resp), 400
    try:
        get_video_by_name(json['cameras'][-1])
        get_video_by_name(json['screens'][-1])
    except:
        Thread(target=process_wait, kwargs={**json}, daemon=True).start()
        return "Videos are not uploaded yet", 200
    Thread(target=hstack_camera_and_screen,
           kwargs={**json}, daemon=True).start()
    return "Merge event added to queue", 201


if __name__ == '__main__':
    app.run()
