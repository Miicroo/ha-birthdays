# Birthdays
This is a HomeAssistant component for tracking birthdays, where the state of each birthday is equal to how many days are left. All birthdays are updated at midnight.

## Installation

### HACS (recommended)
1. Go to integrations
2. Press the dotted menu in the top right corner
3. Choose custom repositories
4. Add the URL to this repository
5. Choose category `Integration`
6. Click add

### Manual
1. In your homeassistant config directory, create a new directory. The path should look like this: **my-ha-config-dir/custom_components
2. Copy the contents of /custom_components in this git-repo to your newly created directory in HA

## Set up
Set up the component:
```yaml
# Example configuration.yaml entry
birthdays:
  - name: 'Frodo Baggins'
    date_of_birth: 1921-09-22
  - name: 'Bilbo Baggins'
    date_of_birth: 1843-09-22
  - name: Elvis
    date_of_birth: 1935-01-08
    icon: 'mdi:music'
```

You can also add a custom `unique_id` and attributes to each birthday, for instance to add an icon or other metadata.
```yaml
  - unique_id: bond_james_bond
    name: James Bond
    date_of_birth: 1920-05-25
    icon: 'mdi:pistol'
    attributes:
      occupation: "Agent"
      license_to_kill: "Yes"
  - unique_id: einstein
    name: 'Albert Einstein'
    date_of_birth: 1879-03-14
    icon: 'mdi:lightbulb-on'
    attributes:
      occupation: 'Theoretical physicist'
      iq: 'Genius level'
      sense_of_humor: 'Einsteinian'
```
Restart homeassistant

## Entities
All entities that do not have a specified `unique_id` are exposed using the format `birthdays.{name}`. Any character that does not fit the pattern `a-z`, `A-Z`, `0-9`, or `_` will be changed. For instance `Frodo Baggins` will get entity_id `frodo_baggins`, and Swedish names like [`Sven-Göran Eriksson`](https://sv.wikipedia.org/wiki/Sven-G%C3%B6ran_Eriksson) will get entity_id `sven_goran_eriksson`.

## Custom attributes
You can add a unique id and custom attributes to each birthday, for instance to add an icon or other metadata.
To do this, add a dictionary under the `attributes` key in the configuration (see example above). The dictionary can contain any key-value pairs you want, and will be exposed as attributes on the entity.
Fetching the attributes can be done using `state_attr` in a template, for instance `{{ state_attr('birthdays.einstein', 'occupation') }}` will return `Theoretical physicist`.

## Automation
All birthdays are updated at midnight, and when a birthday occurs an event is sent on the HA bus that can be used for automations. The event is called `birthday` and contains the data `name` and `age`. Note that there will be two events fired if two persons have the same birthday.

Sending a push notification for each birthday (with PushBullet) looks like this:
```yaml
automation:
  trigger:
    platform: event
    event_type: 'birthday'
    action:
      service: notify.pushbullet
      data_template:
        title: 'Birthday!'
        message: "{{ trigger.event.data.name }} turns {{ trigger.event.data.age }} today!"
```

If you want to trigger an automation based on a specific name or age, you can use the following:
```yaml
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
```

If you want to have a notification sent to you at a specific time (instead of midnight), you can use a custom templated sensor and a time trigger.
Create the sensor:
~~~
template:
  - sensor:
      - name: "Next birthday"
        unique_id: next_birthday
        state: >
          {%- set ns = namespace(days=365) -%}
          {%- for birthday in states.birthdays -%}
            {%- set daysLeft = birthday.state | int -%}
            {%- if daysLeft < ns.days -%}
              {%- set ns.days = daysLeft -%}
            {%- endif -%}
          {%- endfor -%}
          {{ ns.days }}
        attributes:
          names: >
            {%- set ns = namespace(days=365, names=[]) -%}
            {%- for birthday in states.birthdays -%}
              {%- set daysLeft = birthday.state | int -%}
              {%- if daysLeft < ns.days -%}
                {%- set ns.days = daysLeft -%}
              {%- endif -%}
            {%- endfor -%}
            {%- for birthday in states.birthdays -%}
              {%- set daysLeft = birthday.state | int -%}
              {%- if daysLeft == ns.days -%}
                {%- set ns.names = ns.names + [birthday.attributes.friendly_name] -%}
              {%- endif -%}
            {%- endfor -%}
  
            {{ns.names | join(', ')}}
          ages: >
            {%- set ns = namespace(days=365, ages=[]) -%}
            {%- for birthday in states.birthdays -%}
              {%- set daysLeft = birthday.state | int -%}
              {%- if daysLeft < ns.days -%}
                {%- set ns.days = daysLeft -%}
              {%- endif -%}
            {%- endfor -%}
            {%- for birthday in states.birthdays -%}
              {%- set daysLeft = birthday.state | int -%}
              {%- if daysLeft == ns.days -%}
                {%- set ns.ages = ns.ages + [birthday.attributes.age_at_next_birthday] -%}
              {%- endif -%}
            {%- endfor -%}
  
            {{ns.ages | join(', ')}}
          birthday_message: >
            {%- set ns = namespace(days=365, messages=[]) -%}
            {%- for birthday in states.birthdays -%}
              {%- set daysLeft = birthday.state | int -%}
              {%- if daysLeft < ns.days -%}
                {%- set ns.days = daysLeft -%}
              {%- endif -%}
            {%- endfor -%}
            {%- for birthday in states.birthdays -%}
              {%- set daysLeft = birthday.state | int -%}
              {%- if daysLeft == ns.days -%}
                {%- set ns.messages = ns.messages + [birthday.attributes.friendly_name + ' fyller ' + (birthday.attributes.age_at_next_birthday | string) + ' idag!'] -%}
              {%- endif -%}
            {%- endfor -%}
  
            {{ns.messages | join('\n')}}
~~~
and the automation:
```yaml
automation:
  alias: Happy birthday
  trigger:
  - platform: time
    at: '19:00:00'
  condition:
  - condition: state
    entity_id: sensor.next_birthday
    state: '0'
  action:
  - service: persistent_notification.create
    data_template:
      title: 'Birthday!'
      message: "{{ state_attr('sensor.next_birthday', 'birthday_message') }}"
```

## Lovelace UI
I use the birthdays as a simple entity list in lovelace, given the above example I use:
```yaml
# Example use in lovelace
- type: entities
  title: Birthdays
  show_header_toggle: false
  entities:
    - birthdays.frodo_baggins
    - birthdays.bilbo_baggins
    - birthdays.elvis
```

Another possibility is to use the auto-entities card. This allows you to sort the birthdays entered, an example:
```
# Example using auto-entities
- type: custom:auto-entities
  show_empty: false
  card:
    title: Verjaardagen
    type: entities
    card_mod:
      style: |
        #states > * {
          margin: 0 !important;
        }
  filter:
    include:
      - entity_id: birthdays*
  sort:
    method: state
    ignore_case: false
    reverse: false
    numeric: true
```


