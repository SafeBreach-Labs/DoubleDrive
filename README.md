# DoubleDrive
A fully-undetectable ransomware that utilizes Cloud Drive Services to encrypt target files. Presented at Black Hat USA 2023 Briefing under the title - [**One Drive, Double Agent: Clouded OneDrive Turns Sides**](TODO: add link)

## DoubleDrive Python Package
Implements most of the logic and tools that a DoubleDrive variant needs. In order to create a DoubleDrive variant for a certain cloud storage service, the creator must create 2 different executables using this library's tools:
* An endpoint takeover executable, implements:
  * Undetectible ligitimate logic that syncs local target paths from the target computer to the cloud storage service using a built-in feature of the local cloud storage app
  * Exfiltration of the stolen authentication information so the target local paths acually become accessible from the cloud storage service API
* A doubledrive ransomware exeutable, implements:
  * Recievement of the exfiltrated authentication information from the endpoint takeover executable
  * Encryption of all target files by sending API requests to the cloud storage service


## Cloud Storage Services Specific DoubleDrive Implementions:
### OneDrive
Go into ./onedrive_doubledrive for the specific OneDrive variant
