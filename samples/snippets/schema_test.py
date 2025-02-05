#!/usr/bin/env python

# Copyright 2021 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import uuid

from google.api_core.exceptions import NotFound
from google.cloud.pubsub import PublisherClient, SchemaServiceClient, SubscriberClient
from google.pubsub_v1.types import Encoding
import pytest

import schema

UUID = uuid.uuid4().hex
try:
    PROJECT_ID = os.environ["GOOGLE_CLOUD_PROJECT"]
except KeyError:
    raise KeyError("Need to set GOOGLE_CLOUD_PROJECT as an environment variable.")
AVRO_TOPIC_ID = f"schema-test-avro-topic-{UUID}"
PROTO_TOPIC_ID = f"schema-test-proto-topic-{UUID}"
AVRO_SUBSCRIPTION_ID = f"schema-test-avro-subscription-{UUID}"
PROTO_SUBSCRIPTION_ID = f"schema-test-proto-subscription-{UUID}"
AVRO_SCHEMA_ID = f"schema-test-avro-schema-{UUID}"
PROTO_SCHEMA_ID = f"schema-test-proto-schema-{UUID}"
AVSC_FILE = "resources/us-states.avsc"
PROTO_FILE = "resources/us-states.proto"


@pytest.fixture(scope="module")
def schema_client():
    schema_client = SchemaServiceClient()
    yield schema_client


@pytest.fixture(scope="module")
def avro_schema(schema_client):
    avro_schema_path = schema_client.schema_path(PROJECT_ID, AVRO_SCHEMA_ID)

    yield avro_schema_path

    try:
        schema_client.delete_schema(request={"name": avro_schema_path})
    except NotFound:
        pass


@pytest.fixture(scope="module")
def proto_schema(schema_client):
    proto_schema_path = schema_client.schema_path(PROJECT_ID, PROTO_SCHEMA_ID)

    yield proto_schema_path

    try:
        schema_client.delete_schema(request={"name": proto_schema_path})
    except NotFound:
        pass


@pytest.fixture(scope="module")
def publisher_client():
    yield PublisherClient()


@pytest.fixture(scope="module")
def avro_topic(publisher_client, avro_schema):
    from google.pubsub_v1.types import Encoding

    avro_topic_path = publisher_client.topic_path(PROJECT_ID, AVRO_TOPIC_ID)

    try:
        avro_topic = publisher_client.get_topic(request={"topic": avro_topic_path})
    except NotFound:
        avro_topic = publisher_client.create_topic(
            request={
                "name": avro_topic_path,
                "schema_settings": {
                    "schema": avro_schema,
                    "encoding": Encoding.BINAARY,
                },
            }
        )

    yield avro_topic.name

    publisher_client.delete_topic(request={"topic": avro_topic.name})


@pytest.fixture(scope="module")
def proto_topic(publisher_client, proto_schema):
    proto_topic_path = publisher_client.topic_path(PROJECT_ID, PROTO_TOPIC_ID)

    try:
        proto_topic = publisher_client.get_topic(request={"topic": proto_topic_path})
    except NotFound:
        proto_topic = publisher_client.create_topic(
            request={
                "name": proto_topic_path,
                "schema_settings": {
                    "schema": proto_schema,
                    "encoding": Encoding.BINARY,
                },
            }
        )

    yield proto_topic.name

    publisher_client.delete_topic(request={"topic": proto_topic.name})


@pytest.fixture(scope="module")
def subscriber_client():
    subscriber_client = SubscriberClient()
    yield subscriber_client
    subscriber_client.close()


@pytest.fixture(scope="module")
def avro_subscription(subscriber_client, avro_topic):
    avro_subscription_path = subscriber_client.subscription_path(
        PROJECT_ID, AVRO_SUBSCRIPTION_ID
    )

    try:
        avro_subscription = subscriber_client.get_subscription(
            request={"subscription": avro_subscription_path}
        )
    except NotFound:
        avro_subscription = subscriber_client.create_subscription(
            request={"name": avro_subscription_path, "topic": avro_topic}
        )

    yield avro_subscription.name

    subscriber_client.delete_subscription(
        request={"subscription": avro_subscription.name}
    )


@pytest.fixture(scope="module")
def proto_subscription(subscriber_client, proto_topic):
    proto_subscription_path = subscriber_client.subscription_path(
        PROJECT_ID, PROTO_SUBSCRIPTION_ID
    )

    try:
        proto_subscription = subscriber_client.get_subscription(
            request={"subscription": proto_subscription_path}
        )
    except NotFound:
        proto_subscription = subscriber_client.create_subscription(
            request={"name": proto_subscription_path, "topic": proto_topic}
        )

    yield proto_subscription.name

    subscriber_client.delete_subscription(
        request={"subscription": proto_subscription.name}
    )


def test_create_avro_schema(schema_client, avro_schema, capsys):
    try:
        schema_client.delete_schema(request={"name": avro_schema})
    except NotFound:
        pass

    schema.create_avro_schema(PROJECT_ID, AVRO_SCHEMA_ID, AVSC_FILE)

    out, _ = capsys.readouterr()
    assert "Created a schema using an Avro schema file:" in out
    assert f"{avro_schema}" in out


def test_create_proto_schema(schema_client, proto_schema, capsys):
    try:
        schema_client.delete_schema(request={"name": proto_schema})
    except NotFound:
        pass

    schema.create_proto_schema(PROJECT_ID, PROTO_SCHEMA_ID, PROTO_FILE)

    out, _ = capsys.readouterr()
    assert "Created a schema using a protobuf schema file:" in out
    assert f"{proto_schema}" in out


def test_get_schema(avro_schema, capsys):
    schema.get_schema(PROJECT_ID, AVRO_SCHEMA_ID)
    out, _ = capsys.readouterr()
    assert "Got a schema" in out
    assert f"{avro_schema}" in out


def test_list_schemas(capsys):
    schema.list_schemas(PROJECT_ID)
    out, _ = capsys.readouterr()
    assert "Listed schemas." in out


def test_create_topic_with_schema(avro_schema, capsys):
    schema.create_topic_with_schema(PROJECT_ID, AVRO_TOPIC_ID, AVRO_SCHEMA_ID, "BINARY")
    out, _ = capsys.readouterr()
    assert "Created a topic" in out
    assert f"{AVRO_TOPIC_ID}" in out
    assert f"{avro_schema}" in out
    assert "BINARY" in out or "2" in out


def test_publish_avro_records(avro_schema, avro_topic, capsys):
    schema.publish_avro_records(PROJECT_ID, AVRO_TOPIC_ID, AVSC_FILE)
    out, _ = capsys.readouterr()
    assert "Preparing a binary-encoded message" in out
    assert "Published message ID" in out


def test_subscribe_with_avro_schema(avro_schema, avro_topic, avro_subscription, capsys):
    schema.publish_avro_records(PROJECT_ID, AVRO_TOPIC_ID, AVSC_FILE)

    schema.subscribe_with_avro_schema(PROJECT_ID, AVRO_SUBSCRIPTION_ID, AVSC_FILE, 9)
    out, _ = capsys.readouterr()
    assert "Received a binary-encoded message:" in out


def test_publish_proto_records(proto_topic, capsys):
    schema.publish_proto_messages(PROJECT_ID, PROTO_TOPIC_ID)
    out, _ = capsys.readouterr()
    assert "Preparing a binary-encoded message" in out
    assert "Published message ID" in out


def test_subscribe_with_proto_schema(
    proto_schema, proto_topic, proto_subscription, capsys
):
    schema.publish_proto_messages(PROJECT_ID, PROTO_TOPIC_ID)

    schema.subscribe_with_proto_schema(PROJECT_ID, PROTO_SUBSCRIPTION_ID, 9)
    out, _ = capsys.readouterr()
    assert "Received a binary-encoded message" in out


def test_delete_schema(proto_schema, capsys):
    schema.delete_schema(PROJECT_ID, PROTO_SCHEMA_ID)
    out, _ = capsys.readouterr()
    assert "Deleted a schema" in out
    assert f"{proto_schema}" in out
