/* Copyright 2018 Andrew Cassidy
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

const Service, Characteristic;

//initialize module and types
module.exports = function (homebridge) {
    Service = homebridge.hap.Service;
    Characteristic = homebridge.hap.Characteristic;
    homebridge.registerAccessory("psu-switch-plugin", "3D Printer PSU", psuSwitch);
}

function psuSwitch(log, config) {
    this.log = log;
    this.name = config['name'];
    this.socket = config['socket'];
    
}

psuSwitch.prototype.getServices = function() {
    let informationService = new Service.AccessoryInformation();
    informationService
        .setCharacteristic(Characteristic.Manufacturer, "Andrew Cassidy")
        .setCharacteristic(Characteristic.Model, "3D Printer PSU controller")
        .setCharacteristic(Characteristic.SerialNumber, "987-654-321")

    let switchService = new Service.Switch("Power Switch");
    switchService
        .getCharacteristic(Characteristic.On)
            .on('get', this.getOn.bind(this))
            .on('set', this.setOn.bind(this))

    this.informationService = informationService;
    this.switchService = switchService;
    return [informationService, switchService];
}

psuSwitch.prototype.getOn = function(next) {
    //get the thing
}

psuSwitch.prototype.setOn = function(on, next) {
    //do the thing
}