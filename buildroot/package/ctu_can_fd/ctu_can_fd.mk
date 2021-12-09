################################################################################
#
# ctu_can_fd
#
################################################################################

CTU_CAN_FD_SITE = https://gitlab.fel.cvut.cz/canbus/ctucanfd_ip_core.git
CTU_CAN_FD_SITE_METHOD = git
CTU_CAN_FD_VERSION = 80b3c148078c2070ff3c6b1a87f80206e454482b
CTU_CAN_FD_LICENSE = GPL-2.0+
CTU_CAN_FD_LICENSE_FILES = LICENSE

CTU_CAN_FD_MODULE_SUBDIRS = driver/linux

define CTU_CAN_FD_LINUX_CONFIG_FIXUPS
	$(call KCONFIG_SET_OPT,CONFIG_CAN,m)
	$(call KCONFIG_SET_OPT,CONFIG_CAN_RAW,m)
	$(call KCONFIG_SET_OPT,CONFIG_CAN_BCM,m)
	$(call KCONFIG_SET_OPT,CONFIG_CAN_GW,m)
	$(call KCONFIG_SET_OPT,CONFIG_CAN_DEV,m)
	$(call KCONFIG_ENABLE_OPT,CONFIG_CAN_CALC_BITTIMING)
endef

$(eval $(kernel-module))
$(eval $(generic-package))
