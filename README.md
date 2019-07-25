# Birthdays
This is a HomeAssistant component for tracking birthdays, where the state of each birthday is equal to how many days are left. All birthdays are updated at midnight.

## How to setup

1. In your homeassistant config directory, create a new python file. The path should look like this: **my-ha-config-dir/custom_components/birthdays.py**
2. Copy the contents of birthdays.py in this git-repo to your newly created file in HA
3. Set up the component:
~~~~
# Example configuration.yaml entry
birthdays:
  - name: 'Frodo Baggins'
    date_of_birth: 1921-09-22
  - name: 'Bilbo Baggins'
    date_of_birth: 1843-09-22
  - name: Elvis
    date_of_birth: 1935-01-08
    icon: 'mdi:music'
~~~~
4. Restart homeassistant

## Entities
All entities are exposed using the format `birthday.{name}`. Any character that does not fit the pattern `a-z`, `A-Z`, `0-9`, or `_` will be removed. For instance `Frodo Baggins` will get entity_id `FrodoBaggins`, and Swedish names like [`Sven-Göran Eriksson`](https://sv.wikipedia.org/wiki/Sven-G%C3%B6ran_Eriksson) will get entity_id `SvenGranEriksson`.

## Automation
All birthdays are updated at midnight, and when a birthday occurs an event is sent on the HA bus that can be used for automations. The event is called `birthday` and contains the data `name` and `age`. Note that there will be two events fired if two persons have the same birthday.

Sending a push notification for each birthday (with PushBullet) looks like this:
~~~
automation:
  trigger:
    platform: event
    event_type: 'birthday'
    action:
      service: notify.pushbullet
      data_template:
        title: 'Birthday!'
        message: "{{ trigger.event.data.name }} turns {{ trigger.event.data.age }} today!"
~~~

If you want to trigger an automation based on a specific name or age, you can use the following:
~~~
automation:
  trigger:
    platform: event
    event_type: 'birthday'
    event_data:
      name: Kalle
      # age: 40
    action:
      service: notify.pushbullet
      data_template:
        title: 'Birthday!'
        message: "{{ trigger.event.data.name }} turns {{ trigger.event.data.age }} today!"
~~~

## Lovelace UI
I use the birthdays as a simple entity list in lovelace, given the above example I use:
~~~
# Example use in lovelace
- type: entities
  title: Birthdays
  show_header_toggle: false
  entities:
    - birthday.frodo_baggins
    - birthday.bilbo_baggins
    - birthday.elvis
~~~
