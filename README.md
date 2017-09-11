# Raspberry Pi Thermostat

This is the codebase behind my homebrew RasPi Thermostat. The code that belongs on the Pi is in `thermo_client`.

## What is it?

I decided a Nest would be too expensive for my home (I only have a heater, no Air Conditioning), so I decided to build my own Nest.
The RasPi client connects to a cloud based solution (in this case AWS), using API Gateway, with functions connecting to Lambda, and the database backend based on DynamoDB. Settings can be configured by interfacing with this API, through Web or via an App. I have written a basic Android app to use with the API, but it is well documented and easy to use.

