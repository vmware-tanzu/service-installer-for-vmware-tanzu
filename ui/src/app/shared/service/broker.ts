/*
 * Copyright 2021 VMware, Inc
 * SPDX-License-Identifier: BSD-2-Clause
 */
import { Messenger } from './Messenger';

export default class Broker {
    static messenger = new Messenger();
}
