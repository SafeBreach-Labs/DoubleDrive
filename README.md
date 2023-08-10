# DoubleDrive
A fully-undetectable ransomware that utilizes Cloud Drive Services to encrypt target files. Presented at Black Hat USA 2023 Briefing under the title - [**One Drive, Double Agent: Clouded OneDrive Turns Sides**](https://www.blackhat.com/us-23/briefings/schedule/index.html#one-drive-double-agent-clouded-onedrive-turns-sides-32695)

## DoubleDrive Python Package
Implements most of the logic and tools that a DoubleDrive variant needs. In order to create a DoubleDrive variant for a certain cloud storage service, the creator must create 2 different executables using this library's tools:
* An endpoint takeover executable, implements:
  * Undetectable legitimate logic that syncs local target paths from the target computer to the cloud storage service using a built-in feature of the local cloud storage app
  * Exfiltration of the stolen authentication information so the target local paths become accessible from the cloud storage service API
* A DoubleDrive ransomware executable, implements:
  * Collection of the exfiltrated authentication information that was sent by the endpoint takeover executable
  * Encryption of all target files by sending API requests to the cloud storage service


## Specific Cloud Storage Services Implementations of DoubleDrive:
### OneDrive
Go into ./onedrive_doubledrive for the specific OneDrive variant.
You can read how to use it here: [OneDrive DoubleDrive README](onedrive_doubledrive/README.md)

## Author - Or Yair
* LinkedIn - [Or Yair](https://www.linkedin.com/in/or-yair/)
* Twitter - [@oryair1999](https://twitter.com/oryair1999)
