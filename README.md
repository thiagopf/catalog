# catalog-items

The catalog-items program is used for archive items by category

## Getting Started

### Prerequisites

What things you need to install the software

```
Python 2.7
Vagrant
VirtualBox
sqlalchemy
flask
```
### Installing

#### Python 2.7
```
$ sudo apt install python2.7
```
#### flask
```
$ sudo pip install flask
```
#### sqlalchemy
```
$ sudo pip install sqlalchemy
```
#### psycopg2
```
sudo pip install psycopg2
```

#### VirtualBox
Download and install virtualbox from https://www.virtualbox.org/wiki/Downloads

#### Vagrant
Download and install from https://www.vagrantup.com/downloads.html


### Configurations


#### Virtual Machine
How to setup the virtual Machine. First get the machine Configurations.
```
git clone git@github.com:udacity/fullstack-nanodegree-vm.git
```
Now you have a new folder. Get inside the folder called vagrant like this:
```
$ cd FSND-Virtual-Machine/vagrant/
```
Start your VM
```
$ vagrant up
```
Log on VM
```
$ vagrant ssh
```
### Running
```
$ python project.py
```
### Built With
* [Flask](https://palletsprojects.com/p/flask/) - Python web development framework

## Authors

* **Thiago Pereira Fernandes** - *Initial work* - [thiagopf](https://github.com/thiagopf)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
